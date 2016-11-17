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
            'PrintTalonStart', 'PrintTalon', 'ReportTalon']

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
                    print total_ventas_paid
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

        for m in move:
            invoices_a= Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('move', '=', m.id)])
            invoices_all.append(invoices_a)

        lines = MoveLine.search([('state', '=', 'valid')])
        total_ventas_paid = Decimal(0.0)
        total_paid = Decimal(0.0)
        #print "Todas ", invoices_all

        for i_all in invoices_all:
            if i_all != []:
                for i in i_all:
                    for l in lines:
                        if i.move == l.move:
                            total_ventas_paid = total_ventas_paid + l.debit
                        #print "Total paid ", total_ventas_paid
        total_ventas = total_ventas_paid
        #print "Total ventas ", total_ventas, fiscalyear.start_date, period.start_date
        ats = etree.Element('iva')
        etree.SubElement(ats, 'TipoIDInformante').text = 'R'
        etree.SubElement(ats, 'IdInformante').text = id_informante
        etree.SubElement(ats, 'razonSocial').text = name.replace('.', '')
        etree.SubElement(ats, 'Anio').text = fiscalyear.start_date.strftime('%Y')
        etree.SubElement(ats, 'Mes').text = period.start_date.strftime('%m')
        #numero de establecimientos del emisor->entero
        etree.SubElement(ats, 'numEstabRuc').text = '001'
        etree.SubElement(ats, 'totalVentas').text = '0.00'
        etree.SubElement(ats, 'codigoOperativo').text = 'IVA'
        compras = etree.Element('compras')

        invoices = Invoice.search([('state','in',['posted','paid']), ('type','=','in_invoice'), ("invoice_date", '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
        subtotal0 = Decimal(0.00)
        subtotal14 = Decimal(0.00)
        pool = Pool()
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')


        for inv in invoices:
            for line in inv.lines:
                taxes1 = None
                taxes2 = None
                taxes3 = None
                if line.product.taxes_category == True:
                    if line.product.category.taxes_parent == True:
                        taxes1= Taxes1.search([('category','=', line.product.category.parent)])
                    else:
                        taxes1= Taxes1.search([('category','=', line.product.category)])
                else:
                    taxes3 = Taxes2.search([('product','=', line.product)])
                if taxes1:
                    for t in taxes1:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal14 + (line.amount)
                elif taxes2:
                    for t in taxes2:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal0 + (line.amount)
                elif taxes3:
                    for t in taxes3:
                        if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                            subtotal0= subtotal0 + (line.amount)
                        if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                            subtotal14= subtotal14 + (line.amount)

            basegrav = inv.untaxed_amount - subtotal0
            detallecompras = etree.Element('detalleCompras')
            if inv.party.tipo_sustento:
                etree.SubElement(detallecompras, 'codSustento').text = inv.party.tipo_sustento.code
            else:
                inv.raise_user_error('No ha configurado el tipo de sustento del tercero %s. \nDirijase a Terceros->Terceros->Seleccione y modifique', inv.party.name)
            etree.SubElement(detallecompras, 'tpIdProv').text = tipoIdentificacion[inv.party.type_document]
            etree.SubElement(detallecompras, 'idProv').text = inv.party.vat_number
            etree.SubElement(detallecompras, 'tipoComprobante').text = tipoDocumento[inv.type]
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
            etree.SubElement(detallecompras, 'baseImpGrav').text = '%.2f'%subtotal14
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
                withholdings_iva = Withholding_iva.search([('number', '=', inv.ref_withholding)])
                for w_iva in withholdings_iva:
                    for w_taxes in w_iva.taxes:
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
            if inv.party.convenio_doble != "NO":
                etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = inv.party.convenio_doble
            else:
                etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = "NA"
            if inv.party.sujeto_retencion != "NO":
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
            if inv.formas_pago_sri and subtotal14 >= Decimal(1000.0):
                formasDePago = etree.Element('formasDePago')
                etree.SubElement(formasDePago, 'formaPago').text = inv.formas_pago_sri.code
                detallecompras.append(formasDePago)

            withholding = None
            if inv.ref_withholding:
                Withholding = pool.get('account.withholding')
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
                etree.SubElement(detallecompras, 'estabRetencion1').text = withholding.number_w[0:3]
                etree.SubElement(detallecompras, 'ptoEmiRetencion1').text = withholding.number_w[4:7]
                etree.SubElement(detallecompras, 'secRetencion1').text = withholding.number_w[8:16]
                if withholding.numero_autorizacion:
                    etree.SubElement(detallecompras, 'autRetencion1').text = withholding.numero_autorizacion
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
        #print "Los terceros ", terceros
        for party in terceros:
            #print "Si ingresa"
            detalleVentas = etree.Element('detalleVentas')
            if party.type_document:
                pass
                etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            else:
                cls.raise_user_error('No ha configurado el tipo de documento del tercero')
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.SubElement(detalleVentas, 'parteRelVtas').text = party.parte_relacional
            #for m in move:
            #print "Move ", move
            invoices_a_p = Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('party', '=',party.id), ('invoice_date', '>=', period.start_date), ('invoice_date', '<=', period.end_date)])
            if invoices_a_p != []:
                invoices_all_party = invoices_a_p
            base = Decimal(0.0)
            mIva = Decimal(0.0)
            subtotal_v_0 = Decimal(0.0)
            subtotal_v_14 = Decimal(0.0)
            etree.SubElement(detalleVentas, 'tipoComprobante').text = '18'
            numeroComprobantes = 0

            if invoices_all_party != []:
                for inv_out in invoices_all_party:
                    if inv_out.formas_pago_sri:
                        forma_pago = inv_out.formas_pago_sri.code
                    else:
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
                            taxes3 = Taxes2.search([('product','=', line.product)])
                        if taxes1:
                            for t in taxes1:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)
                        elif taxes2:
                            for t in taxes2:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)
                        elif taxes3:
                            for t in taxes3:
                                if str('{:.0f}'.format(t.tax.rate*100)) == '0':
                                    subtotal_v_0= subtotal_v_0 + (line.amount)
                                if str('{:.0f}'.format(t.tax.rate*100)) == '14':
                                    subtotal_v_14= subtotal_v_14 + (line.amount)

                    baseImponible = (subtotal_v_14)
                    montoIva = (baseImponible * (14))/100
                    total_de_ventas += inv_out.total_amount
                    numeroComprobantes += 1

            etree.SubElement(detalleVentas, 'tipoEmision').text = "E"
            etree.SubElement(detalleVentas, 'numeroComprobantes').text = str(numeroComprobantes)
            etree.SubElement(detalleVentas, 'baseNoGraIva').text = '0.00' #pendiente
            etree.SubElement(detalleVentas, 'baseImponible').text = '%.2f' % (subtotal_v_0)
            etree.SubElement(detalleVentas, 'baseImpGrav').text = '%.2f' % (subtotal_v_14)
            etree.SubElement(detalleVentas, 'montoIva').text = '%.2f' % (montoIva)
            etree.SubElement(detalleVentas, 'montoIce').text = '0.00'
            etree.SubElement(detalleVentas, 'valorRetIva').text = '0.00' #pendiente
            etree.SubElement(detalleVentas, 'valorRetRenta').text = '0.00' #pendiente
            formasDePago = etree.Element('formasDePago')
            etree.SubElement(formasDePago, 'formaPago').text = forma_pago
            detalleVentas.append(formasDePago)
            ventas.append(detalleVentas)
        ats.append(ventas)


        ventasEstablecimiento = etree.Element('ventasEstablecimiento')
        ventaEst = etree.Element('ventaEst')
        etree.SubElement(ventaEst, 'codEstab').text = '001'
        etree.SubElement(ventaEst, 'ventasEstab').text = '0.00'
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
        #print "Llega"
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        Period = Pool().get('account.period')
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        #print "Pasa **",data
        localcontext['company'] = company
        localcontext['periodo'] = Period(data['fiscalyear'])
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['no_fac_compras'] = Decimal(0.0)
        localcontext['bi0_fac_compras'] = Decimal(0.0)
        localcontext['bi12_fac_compras'] = Decimal(0.0)
        localcontext['noIva_fac_compras'] = Decimal(0.0)
        localcontext['Iva_fac_compras'] = Decimal(0.0)
        localcontext['no_bol_compras'] = Decimal(0.0)
        localcontext['bi0_bol_compras'] = Decimal(0.0)
        localcontext['bi12_bol_compras'] = Decimal(0.0)
        localcontext['noIva_bol_compras'] = Decimal(0.0)
        localcontext['Iva_bol_compras'] = Decimal(0.0)
        localcontext['no_nc_compras'] = Decimal(0.0)
        localcontext['bi0_nc_compras'] = Decimal(0.0)
        localcontext['bi12_nc_compras'] = Decimal(0.0)
        localcontext['noIva_nc_compras'] = Decimal(0.0)
        localcontext['Iva_nc_compras'] = Decimal(0.0)
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
        localcontext['total_reg_compras'] = Decimal(0.0)
        localcontext['total_bi0_compras'] = Decimal(0.0)
        localcontext['total_bi12_compras'] = Decimal(0.0)
        localcontext['total_noIva_compras'] = Decimal(0.0)
        localcontext['total_iva_compras'] = Decimal(0.0)
        localcontext['no_nc_ventas'] = Decimal(0.0)
        localcontext['bi0_nc_ventas'] = Decimal(0.0)
        localcontext['bi12_nc_ventas'] = Decimal(0.0)
        localcontext['noIva_nc_ventas'] = Decimal(0.0)
        localcontext['Iva_nc_ventas'] = Decimal(0.0)
        localcontext['no_fac_ventas'] = Decimal(0.0)
        localcontext['bi0_fac_ventas'] = Decimal(0.0)
        localcontext['bi12_fac_ventas'] = Decimal(0.0)
        localcontext['noIva_fac_ventas'] = Decimal(0.0)
        localcontext['Iva_fac_ventas'] = Decimal(0.0)
        localcontext['total_reg_ventas'] = Decimal(0.0)
        localcontext['total_bi0_ventas'] = Decimal(0.0)
        localcontext['total_bi12_ventas'] = Decimal(0.0)
        localcontext['total_noIva_ventas'] = Decimal(0.0)
        localcontext['total_iva_ventas'] = Decimal(0.0)
        localcontext['anulados'] = Decimal(0.0)
        localcontext['no_303'] = Decimal(0.0)
        localcontext['base_303'] = Decimal(0.0)
        localcontext['retenido_303'] = Decimal(0.0)
        localcontext['no_310'] = Decimal(0.0)
        localcontext['base_310'] = Decimal(0.0)
        localcontext['retenido_310'] = Decimal(0.0)
        localcontext['no_312'] = Decimal(0.0)
        localcontext['base_312'] = Decimal(0.0)
        localcontext['retenido_312'] = Decimal(0.0)
        localcontext['no_320'] = Decimal(0.0)
        localcontext['base_320'] = Decimal(0.0)
        localcontext['retenido_320'] = Decimal(0.0)
        localcontext['no_342'] = Decimal(0.0)
        localcontext['base_342'] = Decimal(0.0)
        localcontext['retenido_342'] = Decimal(0.0)
        localcontext['no_344'] = Decimal(0.0)
        localcontext['base_344'] = Decimal(0.0)
        localcontext['retenido_344'] = Decimal(0.0)
        localcontext['no_retenciones'] = Decimal(0.0)
        localcontext['base_retenciones'] = Decimal(0.0)
        localcontext['retenido_retenciones'] = Decimal(0.0)
        localcontext['retenido_10'] = Decimal(0.0)
        localcontext['retenido_20'] = Decimal(0.0)
        localcontext['retenido_30'] = Decimal(0.0)
        localcontext['retenido_70'] = Decimal(0.0)
        localcontext['retenido_100'] = Decimal(0.0)
        localcontext['total_retenido'] = Decimal(0.0)
        localcontext['iva_retenido_venta'] = Decimal(0.0)
        localcontext['renta_retenido_venta'] = Decimal(0.0)
        #print "localcontext", localcontext

        return super(ReportTalon, cls).parse(report, objects, data, localcontext)
