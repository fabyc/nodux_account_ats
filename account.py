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
    'out_invoice': '01',
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
        print "Transaction ", Transaction().context
        print "Empresa ", company
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
        print "Todas ", invoices_all

        for i_all in invoices_all:
            for i in i_all:
                for l in lines:
                    if i.move == l.move:
                        total_ventas_paid = total_ventas_paid + l.debit
                        print "Total paid ", total_ventas_paid
        total_ventas = total_ventas_paid
        print "Total ventas ", total_ventas, fiscalyear.start_date, period.start_date
        ats = etree.Element('iva')
        etree.SubElement(ats, 'TipoIDInformante').text = 'R'
        etree.SubElement(ats, 'IdInformante').text = id_informante
        etree.SubElement(ats, 'razonSocial').text = name.replace('.', '')
        etree.SubElement(ats, 'Anio').text = fiscalyear.start_date.strftime('%Y')
        etree.SubElement(ats, 'Mes').text = period.start_date.strftime('%m')
        #numero de establecimientos del emisor->entero
        etree.SubElement(ats, 'numEstabRuc').text = '003'
        etree.SubElement(ats, 'totalVentas').text = str(total_ventas)
        etree.SubElement(ats, 'codigoOperativo').text = 'IVA'
        compras = etree.Element('compras')

        invoices = Invoice.search([('state','in',['posted','paid']), ('type','=','in_invoice')])

        for inv in invoices:
            detallecompras = etree.Element('detalleCompras')
            #pendiente codigo de sustento
            etree.SubElement(detallecompras, 'codSustento').text = inv.party.tipo_sustento.code
            etree.SubElement(detallecompras, 'tpIdProv').text = tipoIdentificacion[inv.party.type_document]
            etree.SubElement(detallecompras, 'idProv').text = inv.party.vat_number
            etree.SubElement(detallecompras, 'tipoComprobante').text = tipoDocumento[inv.type]
            if tipoIdentificacion[inv.party.type_document] == '03':
                etree.SubElement(detallecompras, 'tipoProv').text = tipoProvedor[inv.party.type_party]
            etree.SubElement(detallecompras, 'parteRelVtas').text = inv.party.parte_relacional
            etree.SubElement(detallecompras, 'fechaRegistro').text = inv.invoice_date.strftime('%d/%m/%Y')
            etree.SubElement(detallecompras, 'establecimiento').text = '001'
            etree.SubElement(detallecompras, 'puntoEmision').text = '001'
            etree.SubElement(detallecompras, 'secuencial').text = inv.number
            etree.SubElement(detallecompras, 'fechaEmision').text = inv.invoice_date.strftime('%d/%m/%Y')
            etree.SubElement(detallecompras, 'autorizacion').text = inv.numero_autorizacion
            etree.SubElement(detallecompras, 'baseNoGraIva').text = '001' #corregir
            etree.SubElement(detallecompras, 'baseImponible').text = '001' #corregir
            etree.SubElement(detallecompras, 'baseImpGrav').text = '%.2f'%inv.untaxed_amount
            etree.SubElement(detallecompras, 'montoIce').text = '0.00'
            etree.SubElement(detallecompras, 'montoIva').text = '%.2f'%inv.tax_amount
            etree.SubElement(detallecompras, 'valorRetBienes').text = '%.2f'%abs(inv.tax_amount)

            etree.SubElement(detallecompras, 'valorRetServicios').text = '000' #corregir'%.2f'
            etree.SubElement(detallecompras, 'valRetServ100').text = '000' #corregir'%.2f'
            pagoExterior = etree.Element('pagoExterior')
            etree.SubElement(pagoExterior, 'pagoLocExt').text = inv.party.tipo_de_pago

            etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = inv.party.convenio_doble
            etree.SubElement(pagoExterior, 'pagExtSujRetNorLeg').text = inv.party.sujeto_retencion
            etree.SubElement(pagoExterior, 'pagoRegFis').text = inv.party.pago_regimen
            detallecompras.append(pagoExterior)
            """
            if inv.formas_de_pago:
                formasDePago = etree.Element('formasDePago')
                etree.SubElement(formasDePago, 'formaPago').text = inv.formas_de_pago
                detallecompras.append(formasDePago)
            """
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
                        etree.SubElement(detalleAir, 'codRetAir').text = tax.tax.code_electronic.code
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
                etree.SubElement(detallecompras, 'autRetencion1').text = '000' #pendiente
                etree.SubElement(detallecompras, 'fechaEmiRet1').text = '000' #pendiente
                etree.SubElement(detallecompras, 'docModificado').text = '0'
                etree.SubElement(detallecompras, 'estabModificado').text = '000'
                etree.SubElement(detallecompras, 'ptoEmiModificado').text = '000'
                etree.SubElement(detallecompras, 'secModificado').text = '0'
                etree.SubElement(detallecompras, 'autModificado').text = '0000'
            compras.append(detallecompras)
        ats.append(compras)
        partys = Party.search([('active', '=','true')])
        invoice_line = InvoiceLine.search([('invoice','!=','')])
        numeroComprobantes = 0
        base_parcial = 0
        base_imponible = 0
        montoIva = 0
        ventas_establecimiento = 0
        baseImponible = 0

        ventas = etree.Element('ventas')
        terceros = []
        for inv_all in invoices_all:
            for i_p in inv_all:
                if i_p.party in terceros:
                    pass
                else:
                    terceros.append(i_p.party)
        print "Terceros", terceros
        invoices_all_party= []

        for party in terceros:
            print "El tercero ", party, party.id
            detalleVentas = etree.Element('detalleVentas')
            if party.type_document:
                etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            else:
                cls.raise_user_error('No ha configurado el tipo de documento del tercero')
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.SubElement(detalleVentas, 'parteRelVtas').text = party.parte_relacional
            for m in move:
                print "Move ", move
                invoices_a_p= Invoice.search([('type','=','out_invoice'), ('state','in',['posted','paid']), ('move', '=', m.id), ('party', '=',party.id)])
                invoices_all_party.append(invoices_a_p)
                print "Todas del tercero", invoices_all_party
            base = Decimal(0.0)
            mIva = Decimal(0.0)
            etree.SubElement(detalleVentas, 'tipoComprobante').text = '01'

            for inv_outs in invoices_all_party:
                for inv_out in inv_outs:
                    print "La factura es : ", inv_out
                    for i_line in invoice_line:
                        print "Daots de suma inicial", base_parcial, baseImponible, montoIva
                        print "atos de factura ",i_line.invoice.id, inv_out.id
                        if i_line.invoice.id == inv_out.id:
                            base_parcial = (i_line.unit_price)*Decimal(i_line.quantity)
                            baseImponible = base_parcial + base_imponible
                            montoIva = (baseImponible * (12))/100
                            print "Datos de suma ", base_parcial, baseImponible, montoIva

                    base = baseImponible + base
                    mIva = mIva + montoIva
                numeroComprobantes = numeroComprobantes + 1

                print "base ", baseImponible, base, montoIva, mIva
            print "El numero de comprobante", numeroComprobantes
            etree.SubElement(detalleVentas, 'numeroComprobantes').text = str(numeroComprobantes)
            etree.SubElement(detalleVentas, 'baseNoGraIva').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'baseImponible').text = '%.2f' % (base)
            etree.SubElement(detalleVentas, 'baseImpGrav').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'montoIva').text = '%.2f' % (mIva)
            etree.SubElement(detalleVentas, 'valorRetIva').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'valorRetRenta').text = '000' #pendiente
            ventas.append(detalleVentas)
            ats.append(ventas)
            ventas_establecimiento = baseImponible + ventas_establecimiento

        """ Ventas establecimiento """

        ventasEstablecimiento = etree.Element('ventasEstablecimiento')
        ventaEst = etree.Element('ventaEst')
        etree.SubElement(ventaEst, 'codEstab').text = '001' #pendiente
        etree.SubElement(ventaEst, 'ventasEstab').text = '000' #pendiente
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
        file_ats = etree.tostring(ats, pretty_print=True, encoding='iso-8859-1')
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
        buf.close()
        #name = "%s%s%s.XML" % ("AT", period_id.name[:2], period_id.name[3:8])
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
            'fiscalyear' : self.start.fiscalyear,
            'periodo' : self.start.periodo
            }
        return action, data

    def transition_print_(self):
        return 'end'

class ReportTalon(Report):
    'Report Talon'
    __name__ = 'nodux_account_ats.talon'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        print "Llega"
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        Period = Pool().get('account.period')
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        print "Pasa **",data
        localcontext['company'] = company
        localcontext['periodo'] = Period(data['fiscalyear'])
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['no_fac_compras']= Decimal(0.0)
        localcontext['bi0_fac_compras']= Decimal(0.0)
        localcontext['bi12_fac_compras']= Decimal(0.0)
        localcontext['noIva_fac_compras']= Decimal(0.0)
        localcontext['Iva_fac_compras']= Decimal(0.0)
        localcontext['no_bol_compras']= Decimal(0.0)
        localcontext['bi0_bol_compras']= Decimal(0.0)
        localcontext['bi12_bol_compras']= Decimal(0.0)
        localcontext['noIva_bol_compras']= Decimal(0.0)
        localcontext['Iva_bol_compras']= Decimal(0.0)
        localcontext['no_nc_compras']= Decimal(0.0)
        localcontext['bi0_nc_compras']= Decimal(0.0)
        localcontext['bi12_nc_compras']= Decimal(0.0)
        localcontext['noIva_nc_compras']= Decimal(0.0)
        localcontext['Iva_nc_compras']= Decimal(0.0)
        localcontext['no_cp_compras']= Decimal(0.0)
        localcontext['bi0_cp_compras']= Decimal(0.0)
        localcontext['bi12_cp_compras']= Decimal(0.0)
        localcontext['noIva_cp_compras']= Decimal(0.0)
        localcontext['Iva_cp_compras']= Decimal(0.0)
        localcontext['no_estado_compras']= Decimal(0.0)
        localcontext['bi0_estado_compras']= Decimal(0.0)
        localcontext['bi12_estado_compras']= Decimal(0.0)
        localcontext['noIva_estado_compras']= Decimal(0.0)
        localcontext['Iva_estado_compras']= Decimal(0.0)
        localcontext['total_reg_compras']= Decimal(0.0)
        localcontext['total_bi0_compras']= Decimal(0.0)
        localcontext['total_bi12_compras']= Decimal(0.0)
        localcontext['total_noIva_compras']= Decimal(0.0)
        localcontext['total_iva_compras']= Decimal(0.0)
        localcontext['no_nc_ventas']=Decimal(0.0)
        localcontext['bi0_nc_ventas']=Decimal(0.0)
        localcontext['bi12_nc_ventas']=Decimal(0.0)
        localcontext['noIva_nc_ventas']=Decimal(0.0)
        localcontext['Iva_nc_ventas']=Decimal(0.0)
        localcontext['no_fac_ventas']=Decimal(0.0)
        localcontext['bi0_fac_ventas']=Decimal(0.0)
        localcontext['bi12_fac_ventas']=Decimal(0.0)
        localcontext['noIva_fac_ventas']=Decimal(0.0)
        localcontext['Iva_fac_ventas']=Decimal(0.0)
        localcontext['total_reg_ventas']=Decimal(0.0)
        localcontext['total_bi0_ventas']=Decimal(0.0)
        localcontext['total_bi12_ventas']=Decimal(0.0)
        localcontext['total_noIva_ventas']=Decimal(0.0)
        localcontext['total_iva_ventas']=Decimal(0.0)
        localcontext['anulados']=Decimal(0.0)
        localcontext['no_303']=Decimal(0.0)
        localcontext['base_303']=Decimal(0.0)
        localcontext['retenido_303']=Decimal(0.0)
        localcontext['no_310']=Decimal(0.0)
        localcontext['base_310']=Decimal(0.0)
        localcontext['retenido_310']=Decimal(0.0)
        localcontext['no_312']=Decimal(0.0)
        localcontext['base_312']=Decimal(0.0)
        localcontext['retenido_312']=Decimal(0.0)
        localcontext['no_320']=Decimal(0.0)
        localcontext['base_320']=Decimal(0.0)
        localcontext['retenido_320']=Decimal(0.0)
        localcontext['no_342']=Decimal(0.0)
        localcontext['base_342']=Decimal(0.0)
        localcontext['retenido_342']=Decimal(0.0)
        localcontext['no_344']=Decimal(0.0)
        localcontext['base_344']=Decimal(0.0)
        localcontext['retenido_344']=Decimal(0.0)
        localcontext['no_retenciones']=Decimal(0.0)
        localcontext['base_retenciones']=Decimal(0.0)
        localcontext['retenido_retenciones']=Decimal(0.0)
        localcontext['retenido_10']=Decimal(0.0)
        localcontext['retenido_20']=Decimal(0.0)
        localcontext['retenido_30']=Decimal(0.0)
        localcontext['retenido_70']=Decimal(0.0)
        localcontext['retenido_100']=Decimal(0.0)
        localcontext['total_retenido']=Decimal(0.0)
        localcontext['iva_retenido_venta']=Decimal(0.0)
        localcontext['renta_retenido_venta']=Decimal(0.0)
        print "localcontext", localcontext

        return super(ReportTalon, cls).parse(report, objects, data, localcontext)
