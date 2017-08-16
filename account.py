# -*- coding: utf-8 -*-

#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
from datetime import date
import operator
from sql.aggregate import Sum
from itertools import izip, groupby
from collections import OrderedDict
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateAction, Button, StateTransition, StateAction
from trytond.report import Report
from trytond.pyson import Eval, PYSONEncoder, In
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.modules.company import CompanyReport
import xml.etree.ElementTree
import xml.etree.cElementTree as ET
from lxml import etree
from lxml.etree import DocumentInvalid
from xml.dom.minidom import parse, parseString
import time
import datetime
import smtplib, os
from cStringIO import StringIO as StringIO
import base64
import pytz
from datetime import datetime,timedelta
import time


__all__ = ['SustentoComprobante', 'ATSStart','ATSExportResult', 'ATSExport',
            'PrintTalonStart', 'PrintTalon', 'ReportTalon', 'ReportSummaryPurchases',
            'GenerateSummaryPurchases', 'GenerateSummaryPurchasesStart']

__metaclass__ = PoolMeta

tipoIdentificacion = {
    '04' : '01',
    '05' : '02',
    '06' : '03',
    '07' : '01'
}

identificacionCliente = {
    '04': '04',
    '05': '05',
    '06': '06',
    '07': '07',
    }

tipoDocumento = {
    'out_invoice': '18',
    'out_credit_note': '04',
    'out_debit_note': '05',
    'out_shipment': '06',
    'in_withholding': '07',
    'in_invoice': '01',
}

tpIdCliente = {
    'ruc': '04',
    'cedula': '05',
    'pasaporte': '06',
    }

tipoProvedor = {
    'persona_natural' : '01',
    'sociedad': '02',
}

class SustentoComprobante(ModelSQL, ModelView):
    'Sustento Comprobante'
    __name__ = 'account.sustento'
    name = fields.Char('Tipo de sustento', size=None, required=True, translate=True)
    code = fields.Char('Codigo', size=None, required=True)

    @classmethod
    def __setup__(cls):
        super(SustentoComprobante, cls).__setup__()

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('code',) + tuple(clause[1:]),
            (cls._rec_name,) + tuple(clause[1:]),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.name
        else:
            return self.name

class ATSStart(ModelView):
    'Print ATS'
    __name__ = 'nodux_account_ats.print_ats.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    periodo = fields.Many2One('account.period', 'Period',
        domain=[('fiscalyear', '=', Eval('fiscalyear'))], required = True )

    def get_ventas(self):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        MoveLine = pool.get('account.move.line')
        invoices_paid= Invoice.search([('type','=','out_invoice'), ('state','=', 'paid')])
        invoices_posted = Invoice.search([('state','=', 'posted'), ('type','=','out_invoice')])
        lines = MoveLine.search([('state', '=', 'valid')])
        total_ventas_paid = 0
        total_ventas_posted = 0


        for i in invoices_paid:
            for l in lines:
                if i.move == l.move:
                    total_ventas_paid = total_ventas_paid + l.debit
        for i2 in invoices_posted:
            for l2 in lines:
                if i2.move == l2.move:
                    total_ventas_posted = total_ventas_posted + l2.debit
        total_ventas = total_ventas_paid + total_ventas_posted
        return total_ventas

    @classmethod
    def generate_ats(cls, data):
        pool = Pool()
        Party = pool.get('party.party')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Account = pool.get('account.account')
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        Company = pool.get('company.company')
        Date = pool.get('ir.date')
        Journal = pool.get('account.journal')
        Period = pool.get('account.period')
        FiscalYear = pool.get('account.fiscalyear')
        fiscalyear = FiscalYear(data['fiscalyear'])
        period = Period(data['periodo'])

        company = Company.search([('id', '=', Transaction().context.get('company'))])
        for c in company:
            c_=c
            id_informante = c.party.vat_number
            name = c.party.name

        #para total_ventas
        move = Move.search([('period', '=', period)])
        invoices_all = []
        credits_all = Invoice.search([('type','=','out_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        for m in move:
            invoices_a= Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('move', '=', m.id)])
            invoices_all.append(invoices_a)

        lines = MoveLine.search([('state', '=', 'valid')])
        total_ventas_paid = Decimal(0.0)
        total_ventas_paid1 = Decimal(0.0)
        total_paid = Decimal(0.0)


        for i_all in invoices_all:
            if i_all != []:
                for i in i_all:
                    total_ventas_paid1 += i.untaxed_amount
                    for l in lines:
                        if i.move == l.move:
                            total_ventas_paid = total_ventas_paid + l.debit
        total_ventas = total_ventas_paid1
        ats = etree.Element('iva')
        etree.SubElement(ats, 'TipoIDInformante').text = 'R'
        etree.SubElement(ats, 'IdInformante').text = id_informante
        etree.SubElement(ats, 'razonSocial').text = name.replace('.', '')
        etree.SubElement(ats, 'Anio').text = fiscalyear.start_date.strftime('%Y')
        etree.SubElement(ats, 'Mes').text = period.start_date.strftime('%m')
        #numero de establecimientos del emisor->entero
        etree.SubElement(ats, 'numEstabRuc').text = '001'
        etree.SubElement(ats, 'totalVentas').text =  '%.2f'%total_ventas
        etree.SubElement(ats, 'codigoOperativo').text = 'IVA'
        compras = etree.Element('compras')

        invoices = Invoice.search([('state','in',['posted','paid']), ('type','=','in_invoice'), ("invoice_date", '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        pool = Pool()
        Taxes1I = pool.get('product.category-supplier-account.tax')
        Taxes2I = pool.get('product.template-supplier-account.tax')
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')

        for inv in invoices:
            subtotal14 = Decimal(0.0)
            subtotal0 = Decimal(0.0)
            subtotal12 = Decimal(0.0)
            for line in inv.lines:
                taxes1 = None
                taxes2 = None
                taxes3 = None
                if line.product.taxes_category == True:
                    if line.product.category.taxes_parent == True:
                        taxes1= Taxes1I.search([('category','=', line.product.category.parent)])
                    else:
                        taxes2= Taxes1I.search([('category','=', line.product.category)])
                else:
                    taxes3 = Taxes2I.search([('product','=', line.product.template)])

                if taxes1:
                    for t in taxes1:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal14 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                            subtotal12= subtotal12 + (line.amount)
                elif taxes2:
                    for t in taxes2:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                            subtotal12= subtotal12 + (line.amount)
                elif taxes3:
                    for t in taxes3:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal14 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                            subtotal12= subtotal12 + (line.amount)

            basegrav = inv.untaxed_amount - subtotal0
            detallecompras = etree.Element('detalleCompras')
            if inv.party.tipo_sustento:
                etree.SubElement(detallecompras, 'codSustento').text = inv.party.tipo_sustento.code
            else:
                inv.raise_user_error('No ha configurado el tipo de sustento del tercero %s. \nDirijase a Terceros->Terceros->Seleccione y modifique', inv.party.name)
            etree.SubElement(detallecompras, 'tpIdProv').text = tipoIdentificacion[inv.party.type_document]
            etree.SubElement(detallecompras, 'idProv').text = inv.party.vat_number
            if inv.sale_note != True:
                etree.SubElement(detallecompras, 'tipoComprobante').text = tipoDocumento[inv.type]
            else:
                etree.SubElement(detallecompras, 'tipoComprobante').text = '02'
            etree.SubElement(detallecompras, 'parteRel').text = inv.party.parte_relacional
            if tipoIdentificacion[inv.party.type_document] == '03':
                etree.SubElement(detallecompras, 'tipoProv').text = tipoProvedor[inv.party.type_party]
            etree.SubElement(detallecompras, 'fechaRegistro').text = inv.invoice_date.strftime('%d/%m/%Y')
            etree.SubElement(detallecompras, 'establecimiento').text = inv.reference[0:3]
            etree.SubElement(detallecompras, 'puntoEmision').text = inv.reference[4:7]
            etree.SubElement(detallecompras, 'secuencial').text = inv.reference[8:17]
            etree.SubElement(detallecompras, 'fechaEmision').text = inv.invoice_date.strftime('%d/%m/%Y')
            #if inv.numero_autorizacion_invoice:
            etree.SubElement(detallecompras, 'autorizacion').text = inv.numero_autorizacion_invoice
            etree.SubElement(detallecompras, 'baseNoGraIva').text = '0.00'
            etree.SubElement(detallecompras, 'baseImponible').text = '%.2f'%subtotal0
            etree.SubElement(detallecompras, 'baseImpGrav').text = '%.2f'% (subtotal14+subtotal12)
            etree.SubElement(detallecompras, 'baseImpExe').text = '0.00'
            etree.SubElement(detallecompras, 'montoIce').text = '0.00'
            etree.SubElement(detallecompras, 'montoIva').text = '%.2f'%inv.tax_amount
            withholding_iva = None
            valRetBien10 = Decimal(0.0)
            valRetServ20 = Decimal(0.0)
            valorRetBienes = Decimal(0.0)
            valRetServ50 = Decimal(0.0)
            valorRetServicios = Decimal(0.0)
            valRetServ100 = Decimal(0.0)
            if inv.ref_withholding:
                Withholding_iva = pool.get('account.withholding')
                Withholding_tax = pool.get('account.withholding.tax')
                #withholdings_iva = Withholding_iva.search([('number', '=', inv.ref_withholding), ('fisic', '=', False)])
                withholdings_iva = Withholding_iva.search([('number', '=', inv.ref_withholding)])
                for w_iva in withholdings_iva:
                    for w_taxes in w_iva.taxes:
                        if w_taxes.tax.code_electronic:
                            if w_taxes.tax.code_electronic.code == '9':
                                valRetBien10 = w_taxes.amount * (-1)
                            if w_taxes.tax.code_electronic.code == '10':
                                valRetServ20 = w_taxes.amount * (-1)
                            if w_taxes.tax.code_electronic.code == '1':
                                valorRetBienes = w_taxes.amount * (-1)
                            if w_taxes.tax.code_electronic.code == '2':
                                valorRetServicios = w_taxes.amount * (-1)
                            if w_taxes.tax.code_electronic.code == '3':
                                valRetServ100 = w_taxes.amount * (-1)
                        else:
                            self.raise_user_error('Configure el codigo del impuesto%s', w_taxes.description)

            etree.SubElement(detallecompras, 'valRetBien10').text = '%.2f'%valRetBien10
            etree.SubElement(detallecompras, 'valRetServ20').text =  '%.2f'%valRetServ20
            etree.SubElement(detallecompras, 'valorRetBienes').text =  '%.2f'%valorRetBienes
            etree.SubElement(detallecompras, 'valRetServ50').text =  '%.2f'%valRetServ50
            etree.SubElement(detallecompras, 'valorRetServicios').text =  '%.2f'%valorRetServicios
            etree.SubElement(detallecompras, 'valRetServ100').text =  '%.2f'%valRetServ100
            etree.SubElement(detallecompras, 'totbasesImpReemb').text = '0.00'
            pagoExterior = etree.Element('pagoExterior')
            etree.SubElement(pagoExterior, 'pagoLocExt').text = inv.party.tipo_de_pago
            etree.SubElement(pagoExterior, 'paisEfecPago').text = "NA"
            if inv.party.convenio_doble != "NO" and inv.party.convenio_doble != None:
                etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = inv.party.convenio_doble
            else:
                etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = "NA"
            if inv.party.sujeto_retencion != "NO" and inv.party.sujeto_retencion != None:
                etree.SubElement(pagoExterior, 'pagExtSujRetNorLeg').text = inv.party.sujeto_retencion
            else:
                etree.SubElement(pagoExterior, 'pagExtSujRetNorLeg').text = "NA"
            """
            if inv.party.pago_regimen:
                etree.SubElement(pagoExterior, 'pagoRegFis').text = inv.party.pago_regimen
            else:
                etree.SubElement(pagoExterior, 'pagoRegFis').text = "NA"
            detallecompras.append(pagoExterior)
            """
            detallecompras.append(pagoExterior)
            if inv.untaxed_amount >= Decimal(1000.0):
                formasDePago = etree.Element('formasDePago')
                etree.SubElement(formasDePago, 'formaPago').text = '20'
                detallecompras.append(formasDePago)

            withholding = None
            if inv.ref_withholding:
                Withholding = pool.get('account.withholding')
                #withholdings = Withholding.search([('number', '=', inv.ref_withholding), ('fisic', '=', False)])
                withholdings = Withholding.search([('number', '=', inv.ref_withholding)])
                for w in withholdings:
                    withholding = w

            air = etree.Element('air')
            detalleAir = etree.Element('detalleAir')
            if withholding != None:
                for tax in withholding.taxes:
                    if tax.tipo == 'RENTA':
                        if tax.tax.code_electronic:
                            etree.SubElement(detalleAir, 'codRetAir').text = tax.tax.code_electronic.code
                        else:
                            withholding.raise_user_error(u'No ha configurado el codigo del impuesto %s. Dirijase a:\nFinanciero->Configuracion->Impuestos->Impuestos\nSeleciones el impuesto\nAgrgue el codigo en:Codigo para Retencion-Comp. Elect', tax.description)
                        etree.SubElement(detalleAir, 'baseImpAir').text = '{:.2f}'.format(tax.base)
                        etree.SubElement(detalleAir, 'porcentajeAir').text = '{:.2f}'.format(tax.tax.rate * (-100))
                        etree.SubElement(detalleAir, 'valRetAir').text = '{:.2f}'.format(tax.amount*(-1))
                    if (tax.tax.code_electronic.code == '345') |( tax.tax.code_electronic.code == '345A') | (tax.tax.code_electronic.code ==  '346'):
                        etree.SubElement(detalleAir, 'fechaPagoDiv').text = inv.invoice_date.strftime('%d/%m/%Y')
                    if (tax.tax.code_electronic.code == '327') | (tax.tax.code_electronic.code =='330') | (tax.tax.code_electronic.code =='504') | (tax.tax.code_electronic.code=='504D'):
                        etree.SubElement(detalleAir, 'imRentaSoc').text = '000' #pendiente
                        etree.SubElement(detalleAir, 'anioUtDiv').text = '000' #pendiente
                air.append(detalleAir)
                detallecompras.append(air)
                etree.SubElement(detallecompras, 'estabRetencion1').text = withholding.number[0:3]
                etree.SubElement(detallecompras, 'ptoEmiRetencion1').text = withholding.number[4:7]
                etree.SubElement(detallecompras, 'secRetencion1').text = withholding.number[8:17]
                # if withholding.numero_autorizacion:
                #     etree.SubElement(detallecompras, 'autRetencion1').text = withholding.numero_autorizacion
                etree.SubElement(detallecompras, 'fechaEmiRet1').text = withholding.withholding_date.strftime('%d/%m/%Y')
                """
                etree.SubElement(detallecompras, 'docModificado').text = '0'
                etree.SubElement(detallecompras, 'estabModificado').text = '000'
                etree.SubElement(detallecompras, 'ptoEmiModificado').text = '000'
                etree.SubElement(detallecompras, 'secModificado').text = '0'
                etree.SubElement(detallecompras, 'autModificado').text = '0000'
                """
            compras.append(detallecompras)
        ats.append(compras)
        partys = Party.search([('active', '=','true')])
        invoice_line = InvoiceLine.search([('invoice','!=','')])
        base_parcial = Decimal('0.0')
        base_imponible = Decimal('0.0')
        montoIva = Decimal('0.0')
        ventas_establecimiento = Decimal('0.0')
        baseImponible = Decimal('0.0')
        total_de_ventas = 0
        ventas = etree.Element('ventas')
        terceros = []
        for inv_all in invoices_all:
            for i_p in inv_all:
                if i_p.party in terceros:
                    pass
                else:
                    terceros.append(i_p.party)
        invoices_all_party= []
        for party in terceros:
            detalleVentas = etree.Element('detalleVentas')
            if party.type_document:
                pass
                etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            else:
                cls.raise_user_error('No ha configurado el tipo de documento del tercero %s', party.name )
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.SubElement(detalleVentas, 'parteRelVtas').text = party.parte_relacional
            invoices_a_p = Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('party', '=',party.id), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
            if invoices_a_p != []:
                invoices_all_party = invoices_a_p
            base = Decimal(0.0)
            mIva = Decimal(0.0)
            subtotal_v_0 = Decimal(0.0)
            subtotal_v_14 = Decimal(0.0)
            subtotal_v_12 = Decimal(0.0)
            etree.SubElement(detalleVentas, 'tipoComprobante').text = '18'
            numeroComprobantes = 0
            subtotal_v_0 = Decimal(0.0)
            subtotal_v_14 = Decimal(0.0)
            subtotal_v_12 = Decimal(0.0)
            valorRetIva = Decimal(0.0)
            valorRetRenta = Decimal(0.0)

            if invoices_all_party != []:
                for inv_out in invoices_all_party:
                    # if inv_out.formas_pago_sri:
                    #     forma_pago = inv_out.formas_pago_sri.code
                    # else:
                    #     forma_pago = None
                    forma_pago = None
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    for line in inv_out.lines:
                        if line.product.taxes_category == True:
                            if line.product.category.taxes_parent == True:
                                taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                            else:
                                taxes1= Taxes1.search([('category','=', line.product.category)])
                        else:
                            taxes3 = Taxes2.search([('product','=', line.product.template)])
                        if taxes1:
                            for t in taxes1:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                    subtotal_v_12= subtotal_v_12 + (line.amount)
                        elif taxes2:
                            for t in taxes2:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                    subtotal_v_12= subtotal_v_12 + (line.amount)
                        elif taxes3:
                            for t in taxes3:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                    subtotal_v_12= subtotal_v_12 + (line.amount)

                    baseImponible = (subtotal_v_12)
                    montoIva = (baseImponible * (12))/100
                    total_de_ventas += inv_out.total_amount
                    numeroComprobantes += 1

                    withholding_out = None
                    if inv_out.ref_withholding:
                        WithholdingOut = pool.get('account.withholding')
                        withholdings_out = WithholdingOut.search([('number', '=', inv_out.ref_withholding)])
                        for w in withholdings_out:
                            withholding_out = w
                    if withholding_out != None:
                        for tax in withholding_out.taxes:
                            if tax.tipo == 'IVA':
                                valorRetIva += tax.amount * (-1)
                            if tax.tipo == 'RENTA':
                                valorRetRenta += tax.amount *(-1)

                    etree.SubElement(detalleVentas, 'tipoEmision').text = "F"
                    etree.SubElement(detalleVentas, 'numeroComprobantes').text = str(numeroComprobantes)
                    etree.SubElement(detalleVentas, 'baseNoGraIva').text = '0.00'
                    etree.SubElement(detalleVentas, 'baseImponible').text = '%.2f' % (subtotal_v_0)
                    etree.SubElement(detalleVentas, 'baseImpGrav').text = '%.2f' % (subtotal_v_12)
                    etree.SubElement(detalleVentas, 'montoIva').text = '%.2f' % (montoIva)
                    etree.SubElement(detalleVentas, 'montoIce').text = '0.00'
                    etree.SubElement(detalleVentas, 'valorRetIva').text = '%.2f' % (valorRetIva)
                    etree.SubElement(detalleVentas, 'valorRetRenta').text = '%.2f' % (valorRetRenta)
                    formasDePago = etree.Element('formasDePago')
                    etree.SubElement(formasDePago, 'formaPago').text = "20"
                    detalleVentas.append(formasDePago)
                    ventas.append(detalleVentas)

        terceros_credit = []
        for c_p in credits_all:
            if c_p.party in terceros_credit:
                pass
            else:
                terceros_credit.append(c_p.party)
        credits_all_party= []

        for party in terceros_credit:
            detalleVentas = etree.Element('detalleVentas')
            if party.type_document:
                pass
                etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            else:
                cls.raise_user_error('No ha configurado el tipo de documento del tercero', party.name)
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.SubElement(detalleVentas, 'parteRelVtas').text = party.parte_relacional
            credits_a_p = Invoice.search([('type','=','out_credit_note'), ('state','in',['posted','paid']), ('party', '=',party.id), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
            if credits_a_p != []:
                credits_all_party = credits_a_p
            base_nc = Decimal(0.0)
            mIva_nc = Decimal(0.0)
            subtotal_v_0_nc = Decimal(0.0)
            subtotal_v_14_nc = Decimal(0.0)
            etree.SubElement(detalleVentas, 'tipoComprobante').text = '04'
            numeroComprobantes = 0
            valorRetIvaNC = Decimal(0.0)
            valorRetRentaNC = Decimal(0.0)

            if credits_all_party != []:
                for cre_out in credits_all_party:
                    if cre_out.formas_pago_sri:
                        forma_pago = cre_out.formas_pago_sri.code
                    else:
                        forma_pago = None
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    for line in cre_out.lines:
                        if line.product.taxes_category == True:
                            if line.product.category.taxes_parent == True:
                                taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                            else:
                                taxes1= Taxes1.search([('category','=', line.product.category)])
                        else:
                            taxes3 = Taxes2.search([('product','=', line.product.template)])
                        if taxes1:
                            for t in taxes1:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0_nc= subtotal_v_0_nc + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14_nc = subtotal_v_14_nc + (line.amount)
                        elif taxes2:
                            for t in taxes2:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0_nc= subtotal_v_0_nc + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14_nc= subtotal_v_14_nc + (line.amount)
                        elif taxes3:
                            for t in taxes3:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0_nc= subtotal_v_0_nc + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14_nc= subtotal_v_14_nc + (line.amount)

                    baseImponible_nc = (subtotal_v_14_nc)
                    montoIva_nc = (baseImponible_nc * (14))/100
                    total_de_ventas += cre_out.total_amount
                    numeroComprobantes += 1

                    withholding_nc = None
                    if cre_out.ref_withholding:
                        WithholdingNC = pool.get('account.withholding')
                        withholdings_nc = WithholdingNC.search([('number', '=', cre_out.ref_withholding)])
                        for w in withholdings_nc:
                            withholding_nc = w
                    if withholding_nc != None:
                        for tax in withholding_nc.taxes:
                            if tax.tipo == 'IVA':
                                valorRetIvaNC += tax.amount * (-1)
                            if tax.tipo == 'RENTA':
                                valorRetRentaNC += tax.amount *(-1)

            etree.SubElement(detalleVentas, 'tipoEmision').text = "F"
            etree.SubElement(detalleVentas, 'numeroComprobantes').text = str(numeroComprobantes)
            etree.SubElement(detalleVentas, 'baseNoGraIva').text = '0.00'
            etree.SubElement(detalleVentas, 'baseImponible').text = '%.2f' % (subtotal_v_0_nc)
            etree.SubElement(detalleVentas, 'baseImpGrav').text = '%.2f' % (subtotal_v_14_nc)
            etree.SubElement(detalleVentas, 'montoIva').text = '%.2f' % (montoIva_nc)
            etree.SubElement(detalleVentas, 'montoIce').text = '0.00'
            etree.SubElement(detalleVentas, 'valorRetIva').text = '%.2f' % (valorRetIvaNC)
            etree.SubElement(detalleVentas, 'valorRetRenta').text = '%.2f' % (valorRetRentaNC)
            ventas.append(detalleVentas)
        ats.append(ventas)


        ventasEstablecimiento = etree.Element('ventasEstablecimiento')
        ventaEst = etree.Element('ventaEst')
        etree.SubElement(ventaEst, 'codEstab').text = '001'
        etree.SubElement(ventaEst, 'ventasEstab').text = '%.2f'%total_ventas_paid1
        etree.SubElement(ventaEst, 'ivaComp').text = '0.00'
        ventasEstablecimiento.append(ventaEst)
        ats.append(ventasEstablecimiento)
        """Documentos Anulados"""
        anulados = etree.Element('anulados')

        inv_ids = Invoice.search([('state','=', 'cancel'), ('type','=','out_invoice')])
        """
        inv_ids = inv_obj.search([('state','=','cancel'),
                                  ('period_id','=',period_id),
                                  ('type','=','out_invoice'),
                                  ('company_id','=',company_id.id)])

        """
        for inv in inv_ids:
            detalleAnulados = etree.Element('detalleAnulados')
            etree.SubElement(detalleAnulados, 'tipoComprobante').text = inv.journal_id.auth_id.type_id.code
            etree.SubElement(detalleAnulados, 'establecimiento').text = inv.journal_id.auth_id.serie_entidad
            etree.SubElement(detalleAnulados, 'puntoEmision').text = inv.journal_id.auth_id.serie_emision
            etree.SubElement(detalleAnulados, 'secuencialInicio').text = str(int(inv.number[8:]))
            etree.SubElement(detalleAnulados, 'secuencialFin').text = str(int(inv.number[8:]))
            etree.SubElement(detalleAnulados, 'autorizacion').text = inv.journal_id.auth_id.name
            anulados.append(detalleAnulados)

        ats.append(anulados)

        #validar ats de acuerdo a esquema XSD
        MESSAGE_INVALID = u'El sistema genero el XML pero los datos no pasan la validacion XSD. Revise el error: \n %s'
        file_path = os.path.join(os.path.dirname(__file__), 'ats.xsd')
        schema_file = open(file_path)
        #file_ats = etree.tostring(ats, encoding='utf8', method='xml')
        file_ats = etree.tostring(ats, xml_declaration=True, encoding="utf-8")
        #file_ats = etree.tostring(ats, pretty_print=True, encoding='iso-8859-1')
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)

        try:
            xmlschema.assertValid(ats)
        except DocumentInvalid as e:
            print e
            #cls.raise_user_error(MESSAGE_INVALID, str(e))
        buf = StringIO()
        buf.write(file_ats)
        out=base64.encodestring(buf.getvalue())
        name = "%s%s%s.xml" % ("AT",period.name[5:7],  period.name[0:4])
        buf.close()
        return file_ats

class ATSExportResult(ModelView):
    "Export result"
    __name__ = 'nodux_account_ats.ats.export.result'

    file = fields.Binary('File', readonly=True)

class ATSExport(Wizard):
    "Export ATS"
    __name__ = "nodux_account_ats.ats.export"

    start = StateView('nodux_account_ats.print_ats.start',
        'nodux_account_ats.print_ats_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Export', 'export', 'tryton-ok', default=True),
            ])
    export = StateTransition()
    result = StateView('nodux_account_ats.ats.export.result',
        'nodux_account_ats.ats_export_result_view_form', [
            Button('Close', 'end', 'tryton-close'),
            ])

    def transition_export(cls):
        pool = Pool()
        Account = pool.get('nodux_account_ats.print_ats.start')

        if cls.start.fiscalyear:
            anio = cls.start.fiscalyear
        else:
            anio = None

        if cls.start.periodo:
            period = cls.start.periodo
        else:
            period = None
        data = {
            'fiscalyear': anio,
            'periodo': period,
            }
        file_data = Account.generate_ats(data)
        cls.result.file = buffer(file_data) if file_data else None
        return 'result'

    def default_result(cls, fields):
        file_ = cls.result.file
        cls.result.file = False  # No need to store it in session
        return {
            'file': file_,
            }

class PrintTalonStart(ModelView):
    'Print Talon Start'
    __name__ = 'nodux_account_ats.print_talon.start'
    company = fields.Many2One('company.company', 'Company', required=True)
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    periodo = fields.Many2One('account.period', 'Period',
        domain=[('fiscalyear', '=', Eval('fiscalyear'))], required = True )

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

class PrintTalon(Wizard):
    'Print Talon'
    __name__ = 'nodux_account_ats.print_talon'
    start = StateView('nodux_account_ats.print_talon.start',
        'nodux_account_ats.print_talon_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ats.report_talon')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear' : self.start.fiscalyear.id,
            'periodo' : self.start.periodo.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class ReportTalon(Report):
    'Report Talon'
    __name__ = 'nodux_account_ats.talon'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        Period = Pool().get('account.period')
        period = Period(data['periodo'])
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        localcontext['company'] = company
        localcontext['periodo'] = period
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['no_fac_compras'] = cls._get_no_fac_compras(Period, period)
        localcontext['bi0_fac_compras'] = cls._get_bi0_fac_compras(Period, period)
        localcontext['bi12_fac_compras'] = cls._get_bi12_fac_compras(Period, period)
        localcontext['noIva_fac_compras'] = Decimal(0.0)
        localcontext['Iva_fac_compras'] =  company.currency.round((cls._get_bi12_fac_compras(Period, period)) * Decimal(0.12))
        localcontext['no_bol_compras'] = cls._get_no_bol_compras(Period, period)
        localcontext['bi0_bol_compras'] = cls._get_bi0_bol_compras(Period, period)
        localcontext['bi12_bol_compras'] = cls._get_bi12_bol_compras(Period, period)
        localcontext['noIva_bol_compras'] = Decimal(0.0)
        localcontext['Iva_bol_compras'] = company.currency.round((cls._get_bi12_bol_compras(Period, period)) * Decimal(0.12))
        localcontext['no_nc_compras'] = cls._get_no_nc_compras(Period, period)
        localcontext['bi0_nc_compras'] = cls._get_bi0_nc_compras(Period, period)
        localcontext['bi12_nc_compras'] = cls._get_bi12_nc_compras(Period, period)
        localcontext['noIva_nc_compras'] = Decimal(0.0)
        localcontext['Iva_nc_compras'] = company.currency.round((cls._get_bi12_nc_compras(Period, period)) * Decimal(0.12))
        localcontext['no_cp_compras'] = Decimal(0.0)
        localcontext['bi0_cp_compras'] = Decimal(0.0)
        localcontext['bi12_cp_compras'] = Decimal(0.0)
        localcontext['noIva_cp_compras'] = Decimal(0.0)
        localcontext['Iva_cp_compras'] = Decimal(0.0)
        localcontext['no_estado_compras'] = Decimal(0.0)
        localcontext['bi0_estado_compras'] = Decimal(0.0)
        localcontext['bi12_estado_compras'] = Decimal(0.0)
        localcontext['noIva_estado_compras'] = Decimal(0.0)
        localcontext['Iva_estado_compras'] = Decimal(0.0)
        localcontext['total_reg_compras'] = cls._get_no_fac_compras(Period, period)+cls._get_no_nc_compras(Period, period)+cls._get_no_bol_compras(Period, period)
        localcontext['total_bi0_compras'] = cls._get_bi0_fac_compras(Period, period)+cls._get_bi0_nc_compras(Period, period)+cls._get_bi0_bol_compras(Period, period)
        localcontext['total_bi12_compras'] = cls._get_bi12_fac_compras(Period, period)+cls._get_bi12_nc_compras(Period, period)+cls._get_bi12_bol_compras(Period, period)
        localcontext['total_noIva_compras'] = Decimal(0.0)
        localcontext['total_iva_compras'] = company.currency.round(((cls._get_bi12_fac_compras(Period, period)) * Decimal(0.12))+((cls._get_bi12_nc_compras(Period, period)) * Decimal(0.12)))
        localcontext['no_nc_ventas'] = cls._get_no_nc_ventas(Period, period)
        localcontext['bi0_nc_ventas'] = cls._get_bi0_nc_ventas(Period, period)
        localcontext['bi12_nc_ventas'] = cls._get_bi12_nc_ventas(Period, period)
        localcontext['noIva_nc_ventas'] = Decimal(0.0)
        localcontext['Iva_nc_ventas'] = company.currency.round(cls._get_bi12_nc_ventas(Period, period) * Decimal(0.12))
        localcontext['no_fac_ventas'] = cls._get_no_fac_ventas(Period, period)
        localcontext['bi0_fac_ventas'] = cls._get_bi0_fac_ventas(Period, period)
        localcontext['bi12_fac_ventas'] = cls._get_bi12_fac_ventas(Period, period)
        localcontext['noIva_fac_ventas'] = Decimal(0.0)
        localcontext['Iva_fac_ventas'] = company.currency.round(cls._get_bi12_fac_ventas(Period, period) * Decimal(0.12))
        localcontext['total_reg_ventas'] = localcontext['no_nc_ventas'] + localcontext['no_fac_ventas']
        localcontext['total_bi0_ventas'] = localcontext['bi0_nc_ventas'] + localcontext['bi0_fac_ventas']
        localcontext['total_bi12_ventas'] = localcontext['bi12_nc_ventas'] + localcontext['bi12_fac_ventas']
        localcontext['total_noIva_ventas'] = Decimal(0.0)
        localcontext['total_iva_ventas'] = localcontext['Iva_nc_ventas'] + localcontext['Iva_fac_ventas']
        localcontext['anulados'] = cls._get_anulados(Period, period)
        localcontext['withholdings'] = cls._get_resumen_retencion_fuente(Period, period)
        localcontext['no_retenciones'] = cls._get_no_retenciones(Period, period)
        localcontext['base_retenciones'] = cls._get_base_retenciones(Period, period)
        localcontext['no_withholdings'] = cls._get_resumen_no_retencion_fuente(Period, period)
        localcontext['no_genera_retenciones'] = cls._get_no_genera_retenciones(Period, period)
        localcontext['base_no_retenciones'] = cls._get_base_no_retenciones(Period, period)
        localcontext['retenido_retenciones'] = cls._get_retenido_retenciones(Period, period)
        localcontext['retenido_10'] = cls._get_retenido_10(Period, period)
        localcontext['retenido_20'] = cls._get_retenido_20(Period, period)
        localcontext['retenido_30'] = cls._get_retenido_30(Period, period)
        localcontext['retenido_70'] = cls._get_retenido_70(Period, period)
        localcontext['retenido_100'] = cls._get_retenido_100(Period, period)
        monto_retenido = localcontext['retenido_10']+ localcontext['retenido_20'] +localcontext['retenido_30']+localcontext['retenido_70']+localcontext['retenido_100']
        localcontext['total_retenido'] = monto_retenido
        localcontext['iva_retenido_venta'] = cls._get_iva_retenido_venta(Period, period)
        localcontext['renta_retenido_venta'] =  cls._get_renta_retenido_venta(Period, period)
        monto_retenido_venta = localcontext['iva_retenido_venta'] + localcontext['renta_retenido_venta']
        localcontext['total_retenido_venta'] = monto_retenido_venta
        return super(ReportTalon, cls).parse(report, objects, data, localcontext)

    @classmethod
    def _get_no_fac_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search_count([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('sale_note', '=', False)])

        return invoices

    @classmethod
    def _get_bi0_fac_compras(cls, Period, period):
        bi0_fac_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-supplier-account.tax')
        Taxes2 = pool.get('product.template-supplier-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date),('sale_note', '=', False)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1 = Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
        return bi0_fac_compras

    @classmethod
    def _get_bi12_fac_compras(cls, Period, period):
        bi12_fac_compras = Decimal(0.00)
        bi14_fac_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-supplier-account.tax')
        Taxes2 = pool.get('product.template-supplier-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('sale_note', '=', False)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])

                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi14_fac_compras= bi14_fac_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras= bi12_fac_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi14_fac_compras= bi14_fac_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras= bi12_fac_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_fac_compras= bi12_fac_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras= bi12_fac_compras + (line.amount)
        return bi12_fac_compras

    #NOTAS DE venta
    @classmethod
    def _get_no_bol_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search_count([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('sale_note', '=', True)])

        return invoices

    @classmethod
    def _get_bi0_bol_compras(cls, Period, period):
        bi0_bol_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-supplier-account.tax')
        Taxes2 = pool.get('product.template-supplier-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('sale_note', '=', True)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1 = Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_bol_compras= bi0_bol_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_bol_compras= bi0_bol_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_bol_compras= bi0_bol_compras + (line.amount)
        return bi0_bol_compras

    @classmethod
    def _get_bi12_bol_compras(cls, Period, period):
        bi12_bol_compras = Decimal(0.00)
        bi14_bol_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-supplier-account.tax')
        Taxes2 = pool.get('product.template-supplier-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date),('sale_note', '=', True)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])

                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi14_bol_compras= bi14_bol_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_bol_compras= bi12_bol_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi14_bol_compras= bi14_bol_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_bol_compras= bi12_bol_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_bol_compras= bi12_bol_compras + (line.amount)
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_bol_compras= bi12_bol_compras + (line.amount)
        return bi12_bol_compras


    @classmethod
    def _get_no_nc_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        no_nc_compras = 0
        if invoices:
            no_nc_compras = len(invoices)
        return no_nc_compras

    @classmethod
    def _get_bi0_nc_compras(cls, Period, period):
        bi0_nc_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_compras= bi0_nc_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_compras= bi0_nc_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_compras= bi0_nc_compras + (line.amount)
        return bi0_nc_compras

    @classmethod
    def _get_bi12_nc_compras(cls, Period, period):
        bi12_nc_compras = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_compras= bi12_nc_compras + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_compras= bi12_nc_compras + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_compras= bi12_nc_compras + (line.amount)
        return bi12_nc_compras

    @classmethod
    def _get_no_nc_ventas(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        no_nc_ventas = 0
        if invoices:
            no_nc_ventas = len(invoices)
        return no_nc_ventas


    @classmethod
    def _get_bi0_nc_ventas(cls, Period, period):
        bi0_nc_ventas = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_ventas= bi0_nc_ventas + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_ventas= bi0_nc_ventas + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_nc_ventas= bi0_nc_ventas + (line.amount)
        return bi0_nc_ventas

    @classmethod
    def _get_bi12_nc_ventas(cls, Period, period):
        bi12_nc_ventas = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_credit_note'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_ventas= bi12_nc_ventas + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_ventas= bi12_nc_ventas + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                bi12_nc_ventas= bi12_nc_ventas + (line.amount)
        return bi12_nc_ventas

    @classmethod
    def _get_no_fac_ventas(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        no_fac_ventas = 0
        if invoices:
            no_fac_ventas = len(invoices)
        return no_fac_ventas

    @classmethod
    def _get_bi0_fac_ventas(cls, Period, period):
        bi0_fac_ventas = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_ventas= bi0_fac_ventas + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_ventas= bi0_fac_ventas + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_ventas= bi0_fac_ventas + (line.amount)
        return bi0_fac_ventas

    @classmethod
    def _get_bi12_fac_ventas(cls, Period, period):
        bi12_fac_ventas = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])
                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_ventas= bi12_fac_ventas + (line.amount)
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_ventas= bi12_fac_ventas + (line.amount)
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_ventas= bi12_fac_ventas + (line.amount)

        return bi12_fac_ventas

    @classmethod
    def _get_anulados(cls, Period, period):
        anulados = 0
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','out_invoice'), ('state','=', 'annulled'), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        if invoices:
            anulados = lens(invoices)
        return anulados

    @classmethod
    def _get_resumen_retencion_fuente(cls, Period, period):
        resumen_retencion_fuente = []
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state', '!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])
        taxes = []

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tipo == 'RENTA':
                    if w_taxes.description in taxes:
                        pass
                    else:
                        taxes.append(w_taxes.description)

        for tax in taxes:
            lineas = {}
            base = Decimal(0.0)
            retenido = Decimal(0.0)
            cont = 0
            code = ""

            for withholding in withholdings:
                for w_taxes in withholding.taxes:
                    if w_taxes.description == tax:
                        if w_taxes.tax.code_electronic:
                            code = w_taxes.tax.code_electronic.code
                        else:
                            withholding.raise_user_error("Configure el codigo del impuesto \n%s", w_taxes.description)
                        base += w_taxes.base
                        retenido += w_taxes.amount * (-1)
                        cont += 1

            lineas['code'] = code
            lineas['description'] = tax
            lineas['nro_registros'] = cont
            lineas['base'] = base
            lineas['retenido'] = retenido

            resumen_retencion_fuente.append(lineas)
        return resumen_retencion_fuente

    @classmethod
    def _get_resumen_no_retencion_fuente(cls, Period, period):
        resumen_no_retencion_fuente = []
        base = Decimal(0.0)
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state', '!=', 'draft'), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('no_generate_withholding', '=', True)])

        for invoice in invoices:
            for line in invoice.lines:
                base += line.amount

        lineas = {}
        lineas['code'] = 332
        lineas['description'] = u'OTRAS COMPRAS DE BIENES Y SERVICIOS NO SUJETAS A RETENCIÓN (332)'
        lineas['nro_registros'] = len(invoices)
        lineas['base'] = base
        lineas['retenido'] = Decimal(0.0)

        resumen_no_retencion_fuente.append(lineas)
        return resumen_no_retencion_fuente

    @classmethod
    def _get_no_genera_retenciones(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state', '!=', 'draft'), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('no_generate_withholding', '=', True)])

        return len(invoices)


    @classmethod
    def _get_base_no_retenciones(cls, Period, period):
        base = Decimal(0.0)
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state', '!=', 'draft'), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date), ('no_generate_withholding', '=', True)])
        for invoice in invoices:
            base += invoice.untaxed_amount
        return base

    @classmethod
    def _get_no_retenciones(cls, Period, period):
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state', '!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])
        taxes = []
        no_retenciones = 0

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tipo == 'RENTA':
                    if w_taxes.description in taxes:
                        pass
                    else:
                        taxes.append(w_taxes.description)

        for tax in taxes:
            cont = 0
            for withholding in withholdings:
                for w_taxes in withholding.taxes:
                    if w_taxes.description == tax:
                        cont += 1
            no_retenciones += cont
        return no_retenciones

    @classmethod
    def _get_base_retenciones(cls, Period, period):
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state', '!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])
        base = 0

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tipo == 'RENTA':
                    base += w_taxes.base

        return base

    @classmethod
    def _get_retenido_retenciones(cls, Period, period):
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state', '!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])
        retenido = 0

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tipo == 'RENTA':
                    retenido += (w_taxes.amount * (-1))

        return retenido

    @classmethod
    def _get_retenido_10(cls, Period, period):
        retenido_10 = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tax.code_electronic:
                    if w_taxes.tax.code_electronic.code == '9':
                        retenido_10 += w_taxes.amount * (-1)

                else:
                    withholding.raise_user_error('Configure el codigo del impuesto \n%s', w_taxes.description)
        return retenido_10

    @classmethod
    def _get_retenido_20(cls, Period, period):
        retenido_20 = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tax.code_electronic:
                    if w_taxes.tax.code_electronic.code == '10':
                        retenido_20 += w_taxes.amount * (-1)
                else:
                    withholding.raise_user_error('Configure el codigo del impuesto \n%s', w_taxes.description)
        return retenido_20

    @classmethod
    def _get_retenido_30(cls, Period, period):
        retenido_30 = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tax.code_electronic:
                    if w_taxes.tax.code_electronic.code == '1':
                        retenido_30 += w_taxes.amount * (-1)
                else:
                    withholding.raise_user_error('Configure el codigo del impuesto \n%s', w_taxes.description)
        return retenido_30

    @classmethod
    def _get_retenido_70(cls, Period, period):
        retenido_70 = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tax.code_electronic:
                    if w_taxes.tax.code_electronic.code == '2':
                        retenido_70 += w_taxes.amount * (-1)
                else:
                    withholding.raise_user_error('Configure el codigo del impuesto \n%s', w_taxes.description)
        return retenido_70

    @classmethod
    def _get_retenido_100(cls, Period, period):
        retenido_100 = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','in_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if w_taxes.tax.code_electronic:
                    if w_taxes.tax.code_electronic.code == '3':
                        retenido_100 += w_taxes.amount * (-1)
                else:
                    withholding.raise_user_error('Configure el codigo del impuesto \n%s', w_taxes.description)

        return retenido_100

    @classmethod
    def _get_iva_retenido_venta(cls, Period, period):
        iva_retenido_venta = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','out_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if (w_taxes.tipo == 'IVA') | (w_taxes.tax.code_withholding == '2'):
                    iva_retenido_venta += (w_taxes.amount * (-1))
        return iva_retenido_venta

    @classmethod
    def _get_renta_retenido_venta(cls, Period, period):
        renta_retenido_venta = Decimal(0.0)
        pool = Pool()
        Withholding = pool.get('account.withholding')
        withholdings = Withholding.search([('type','=','out_withholding'), ('state','!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])

        for withholding in withholdings:
            for w_taxes in withholding.taxes:
                if (w_taxes.tipo == 'RENTA') | (w_taxes.tax.code_withholding == '1'):
                    renta_retenido_venta += (w_taxes.amount * (-1))
        return renta_retenido_venta


class GenerateSummaryPurchasesStart(ModelView):
    'Generate Purchases Annexed Start'
    __name__ = 'nodux_account_ats.print_sumary_purchases.start'
    company = fields.Many2One('company.company', 'Company', required=True)
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    periodo = fields.Many2One('account.period', 'Period',
        domain=[('fiscalyear', '=', Eval('fiscalyear'))], required = True )

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

class GenerateSummaryPurchases(Wizard):
    'Generate Purchases Annexed'
    __name__ = 'nodux_account_ats.print_sumary_purchases'
    start = StateView('nodux_account_ats.print_sumary_purchases.start',
        'nodux_account_ats.print_sumary_purchases_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ats.report_sumary_purchases')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear' : self.start.fiscalyear.id,
            'periodo' : self.start.periodo.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class ReportSummaryPurchases(Report):
    'Report Purchases Annexed'
    __name__ = 'nodux_account_ats.sumary_purchases'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        Period = Pool().get('account.period')
        period = Period(data['periodo'])
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        localcontext['company'] = company
        localcontext['periodo'] = period
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['purchases'] = cls._get_purchases(Period, period)
        localcontext['total_bi0_fac_compras'] = cls._total_bi0_fac_compras(Period, period)
        localcontext['total_bi12_fac_compras'] = cls._total_bi12_fac_compras(Period, period)
        localcontext['total_iva_fac_compras'] = cls._total_iva_fac_compras(Period, period)
        localcontext['total_fac_compras'] =  cls._total_fac_compras(Period, period)

        return super(ReportSummaryPurchases, cls).parse(report, objects, data, localcontext)

    @classmethod
    def _get_purchases(cls, Period, period):
        pool = Pool()
        Taxes1 = pool.get('product.category-supplier-account.tax')
        Taxes2 = pool.get('product.template-supplier-account.tax')

        Invoice = pool.get('account.invoice')
        Withholding = pool.get('account.withholding')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        total_bi0_fac_compras = Decimal(0.00)
        total_bi12_fac_compras = Decimal(0.00)
        total_iva_fac_compras = Decimal(0.00)
        total_ret_10_fuente = Decimal(0.00)
        total_ret_1_fuente = Decimal(0.00)
        total_ret_2_fuente = Decimal(0.00)
        total_ret_10_iva = Decimal(0.00)
        total_ret_20_iva = Decimal(0.00)
        total_ret_70_iva = Decimal(0.00)
        total_ret_30_iva = Decimal(0.00)
        total_ret_100_iva = Decimal(0.00)
        purchases = []
        cont = 0

        if invoices:
            for invoice in invoices:
                bi0_fac_compras = Decimal(0.00)
                bi12_fac_compras = Decimal(0.00)
                iva_fac_compras = invoice.tax_amount
                total_iva_fac_compras += invoice.tax_amount
                ret_10_fuente = Decimal(0.00)
                ret_1_fuente = Decimal(0.00)
                ret_2_fuente = Decimal(0.00)
                ret_no_fuente = Decimal(0.00)
                ret_10_iva = Decimal(0.00)
                ret_20_iva = Decimal(0.00)
                ret_30_iva = Decimal(0.00)
                ret_70_iva = Decimal(0.00)
                ret_100_iva = Decimal(0.00)
                retencion = ""
                date_w = ""

                withholdings = Withholding.search([('party', '=', invoice.party),('type', '=', 'in_withholding'),('number_w', '=', invoice.reference), ('state', '!=', 'draft'), ('withholding_date', '>=', period.start_date), ('withholding_date', '<=', period.end_date)])
                for withholding in withholdings:
                    retencion = withholding.number
                    date_w = withholding.withholding_date
                    for w_taxes in withholding.taxes:
                        if w_taxes.tipo == 'RENTA':
                            if str('{:.0f}'.format(w_taxes.tax.rate*100)) == '-10':
                                ret_10_fuente = w_taxes.amount * (-1)
                                total_ret_10_fuente += w_taxes.amount * (-1)

                            if str('{:.0f}'.format(w_taxes.tax.rate*100)) == '-1':
                                ret_1_fuente = w_taxes.amount * (-1)
                                total_ret_1_fuente = w_taxes.amount * (-1)

                            if str('{:.0f}'.format(w_taxes.tax.rate*100)) == '-2':
                                ret_2_fuente = w_taxes.amount * (-1)
                                total_ret_2_fuente = w_taxes.amount * (-1)
                        else:
                            if w_taxes.tax.code_electronic:
                                if w_taxes.tax.code_electronic.code == '3':
                                    ret_100_iva = w_taxes.amount * (-1)
                                    total_ret_100_iva = Decimal(0.00)

                                elif w_taxes.tax.code_electronic.code == '9':
                                    ret_10_iva = w_taxes.amount * (-1)
                                    total_ret_10_iva = Decimal(0.00)

                                elif w_taxes.tax.code_electronic.code == '10':
                                    ret_20_iva = w_taxes.amount * (-1)
                                    total_ret_20_iva = Decimal(0.00)

                                elif w_taxes.tax.code_electronic.code == '1':
                                    ret_30_iva = w_taxes.amount * (-1)
                                    total_ret_30_iva = Decimal(0.00)

                                elif w_taxes.tax.code_electronic.code == '2':
                                    ret_70_iva = w_taxes.amount * (-1)
                                    total_ret_70_iva = Decimal(0.00)

                for line in invoice.lines:
                    taxes1 = None
                    taxes2 = None
                    taxes3 = None
                    if line.product.taxes_category == True:
                        if line.product.category.taxes_parent == True:
                            taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                        else:
                            taxes1= Taxes1.search([('category','=', line.product.category)])
                    else:
                        taxes3 = Taxes2.search([('product','=', line.product.template)])

                    if taxes1:
                        for t in taxes1:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
                                total_bi0_fac_compras += line.amount
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras += (line.amount)
                                total_bi12_fac_compras += line.amount
                    elif taxes2:
                        for t in taxes2:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
                                total_bi0_fac_compras += line.amount
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras += (line.amount)
                                total_bi12_fac_compras += line.amount
                    elif taxes3:
                        for t in taxes3:
                            if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                bi0_fac_compras= bi0_fac_compras + (line.amount)
                                total_bi0_fac_compras += line.amount
                            if str('{:.0f}'.format(t.tax.rate*100)) == '12':
                                bi12_fac_compras += (line.amount)
                                total_bi12_fac_compras += line.amount
                cont += 1
                lineas = {}
                lineas['id'] = cont
                lineas['number'] = invoice.reference
                lineas['date'] = invoice.invoice_date
                lineas['subtotal12'] = bi12_fac_compras
                lineas['subtotal0'] = bi0_fac_compras
                lineas['iva'] = iva_fac_compras
                lineas['ret_10_fuente'] = ret_10_fuente
                lineas['ret_1_fuente'] = ret_1_fuente
                lineas['ret_2_fuente'] = ret_2_fuente
                lineas['ret_10_iva'] = ret_10_iva
                lineas['ret_20_iva'] = ret_20_iva
                lineas['ret_30_iva'] = ret_30_iva
                lineas['ret_70_iva'] = ret_70_iva
                lineas['ret_100_iva'] = ret_100_iva
                lineas['retencion'] = retencion
                lineas['date_w'] = date_w

                purchases.append(lineas)

        return purchases

    @classmethod
    def _total_bi0_fac_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        total_bi0_fac_compras= Decimal(0.00)

        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    if  line.taxes:
                        for t in line.taxes:
                            if str('{:.0f}'.format(t.rate*100)) == '0':
                                total_bi0_fac_compras+= line.amount

        return total_bi0_fac_compras

    @classmethod
    def _total_bi12_fac_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        total_bi12_fac_compras= Decimal(0.00)

        if invoices:
            for invoice in invoices:
                for line in invoice.lines:
                    if  line.taxes:
                        for t in line.taxes:
                            if str('{:.0f}'.format(t.rate*100)) == '12':
                                total_bi12_fac_compras+= line.amount

        return total_bi12_fac_compras

    @classmethod
    def _total_iva_fac_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        total_iva_fac_compras= Decimal(0.00)

        if invoices:
            for invoice in invoices:
                total_iva_fac_compras += invoice.tax_amount

        return total_iva_fac_compras

    @classmethod
    def _total_fac_compras(cls, Period, period):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = Invoice.search([('type','=','in_invoice'), ('state','in',['posted','paid']), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        total_fac_compras= Decimal(0.00)
        total_iva_fac_compras = Decimal(0.00)
        total_bi0_fac_compras = Decimal(0.00)
        total_bi12_fac_compras = Decimal(0.00)


        if invoices:
            for invoice in invoices:
                total_iva_fac_compras += invoice.tax_amount
                for line in invoice.lines:
                    if  line.taxes:
                        for t in line.taxes:
                            if str('{:.0f}'.format(t.rate*100)) == '0':
                                total_bi0_fac_compras+= line.amount
                        for t in line.taxes:
                            if str('{:.0f}'.format(t.rate*100)) == '12':
                                total_bi12_fac_compras+= line.amount

            total_fac_compras = (total_iva_fac_compras + total_bi0_fac_compras + total_bi12_fac_compras)

        return total_fac_compras
