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
from trytond.pyson import Eval, PYSONEncoder
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

__all__ = ['ATSStart','ATSExportResult', 'ATSExport']
         
__metaclass__ = PoolMeta

tipoIdentificacion = {
    '04' : '01',
    '05' : '02',
    '06' : '03',
}

identificacionCliente = {
    '04': '04',
    '05': '05',
    '06': '06',
    }

tipoDocumento = {
    'out_invoice': '01',
    'out_credit_note': '04',
    'out_debit_note': '05',
    'out_shipment': '06',
    'in_withholding': '07',
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

class ATSStart(ModelView):
    'Print ATS'
    __name__ = 'nodux_account_ats.print_ats.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    periodo = fields.Many2One('account.period', 'Period',
        domain=[('fiscalyear', '=', Eval('fiscalyear'))], required = True )
        
    def get_ventas(self):
        print "LLEga **"
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
    def generate_ats(cls):
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
        company = Company.search([('id', '=', Transaction().context.get('company'))])
        print "Empresa ", company
        for c in company:
            id_informante = c.party.vat_number
            name = c.party.name
        ats = etree.Element('iva')
        etree.SubElement(ats, 'TipoIDInformante').text = 'R'
        etree.SubElement(ats, 'IdInformante').text = id_informante #corregir
        etree.SubElement(ats, 'razonSocial').text = name #corregir
        etree.SubElement(ats, 'Anio').text = '2016'#corregir time.strftime(cls.periodo.start_date, '%Y') 
        etree.SubElement(ats, 'Mes').text = '03' #corregir time.strftime(cls.periodo.start_date, '%m')        
        #numero de establecimientos del emisor->entero
        etree.SubElement(ats, 'numEstabRuc').text = '003'
        etree.SubElement(ats, 'totalVentas').text = "20065"
        etree.SubElement(ats, 'codigoOperativo').text = 'IVA'
        compras = etree.Element('compras')
        
        invoices = Invoice.search([('state','in',['posted','paid']), ('type','=','in_invoice')])
      
        for inv in invoices:
            detallecompras = etree.Element('detalleCompras')
            #pendiente codigo de sustento
            etree.SubElement(detallecompras, 'codSustento').text = cls.party.type_sustent
            etree.SubElement(detallecompras, 'tpIdProv').text = tipoIdentificacion[cls.party.type_document]
            etree.SubElement(detallecompras, 'idProv').text = cls.party.vat_number
            etree.SubElement(detallecompras, 'tipoComprobante').text = tipoDocumento[cls.type]
            if tipoIdentificacion[cls.party.type_document] == '03':
                etree.SubElement(detallecompras, 'tipoProv').text = tipoProvedor[cls.party.type_party]
            etree.SubElement(detallecompras, 'parteRelVtas').text = cls.party.parte_relacional
            etree.SubElement(detallecompras, 'fechaRegistro').text = time.strftime(inv.date_invoice, '%d/%m/%Y')
            etree.SubElement(detallecompras, 'establecimiento').text = '001'
            etree.SubElement(detallecompras, 'puntoEmision').text = '001'
            etree.SubElement(detallecompras, 'secuencial').text = inv.number
            etree.SubElement(detallecompras, 'fechaEmision').text = time.strftime(inv.date_invoice, '%d/%m/%Y')
            etree.SubElement(detallecompras, 'autorizacion').text = inv.numero_autorizacion
            etree.SubElement(detallecompras, 'baseNoGraIva').text = '001' #corregir
            etree.SubElement(detallecompras, 'baseImponible').text = '001' #corregir
            etree.SubElement(detallecompras, 'baseImpGrav').text = '%.2f'%inv.untaxed_amount
            etree.SubElement(detallecompras, 'montoIce').text = '0.00'
            etree.SubElement(detallecompras, 'montoIva').text = '%.2f'%inv.tax_amount
            etree.SubElement(detallecompras, 'valorRetBienes').text = '%.2f'%abs(inv.tax_amount)
            
            etree.SubElement(detallecompras, 'valorRetServicios').text = '000', #corregir'%.2f'
            etree.SubElement(detallecompras, 'valRetServ100').text = '000', #corregir'%.2f'
            pagoExterior = etree.Element('pagoExterior')
            etree.SubElement(pagoExterior, 'pagoLocExt').text = cls.party.tipo_de_pago
            if cls.party.tipo_de_pago == '02':
                if cls.party.address.country.code == 'GW':
                    codigo_pais = 437
                elif cls.party.address.country.code == 'GU':
                    codigo_pais = 517
                elif cls.party.address.country.code == 'GT':
                    codigo_pais = 111
                elif cls.party.address.country.code == 'GS':
                    codigo_pais = 246
                elif cls.party.address.country.code == 'GR':
                    codigo_pais = 214
                elif cls.party.address.country.code == 'GQ':
                    codigo_pais = 438
                elif cls.party.address.country.code == 'GP':
                    codigo_pais = 143
                elif cls.party.address.country.code == 'GY':
                    codigo_pais = 132
                elif cls.party.address.country.code == 'GG':
                    codigo_pais = 831
                elif cls.party.address.country.code == 'GF':
                    codigo_pais = 144
                elif cls.party.address.country.code == 'GE':
                    codigo_pais = 246
                elif cls.party.address.country.code == 'GD':
                    codigo_pais = 131
                elif cls.party.address.country.code == 'GB':
                    codigo_pais = 213
                elif cls.party.address.country.code == 'GA':
                    codigo_pais = 435
                elif cls.party.address.country.code == 'GN':
                    codigo_pais = 409
                elif cls.party.address.country.code == 'GM':
                    codigo_pais = 408
                elif cls.party.address.country.code == 'GL':
                    codigo_pais = 247
                elif cls.party.address.country.code == 'GI':
                    codigo_pais = 239
                elif cls.party.address.country.code == 'GH':
                    codigo_pais = 436
                elif cls.party.address.country.code == 'LC':
                    codigo_pais = 138
                elif cls.party.address.country.code == 'LB':
                    codigo_pais = 318
                elif cls.party.address.country.code == 'LA':
                    codigo_pais = 122
                elif cls.party.address.country.code == 'TV':
                    codigo_pais = 515
                elif cls.party.address.country.code == 'TW':
                    codigo_pais = 307
                elif cls.party.address.country.code == 'TT':
                    codigo_pais = 124
                elif cls.party.address.country.code == 'TR':
                    codigo_pais = 346
                elif cls.party.address.country.code == 'LK':
                    codigo_pais = 339
                elif cls.party.address.country.code == 'LI':
                    codigo_pais = 234
                elif cls.party.address.country.code == 'LV':
                    codigo_pais = 601
                elif cls.party.address.country.code == 'TO':
                    codigo_pais = 508
                elif cls.party.address.country.code == 'LT':
                    codigo_pais = 249
                elif cls.party.address.country.code == 'LU':
                    codigo_pais = 220
                elif cls.party.address.country.code == 'LR':
                    codigo_pais = 410
                elif cls.party.address.country.code == 'LS':
                    codigo_pais = 440
                elif cls.party.address.country.code == 'TH':
                    codigo_pais = 325
                elif cls.party.address.country.code == 'TF':
                    codigo_pais = 260
                elif cls.party.address.country.code == 'TG':
                    codigo_pais = 451
                elif cls.party.address.country.code == 'TD':
                    codigo_pais = 433
                elif cls.party.address.country.code == 'TC':
                    codigo_pais = 151
                elif cls.party.address.country.code == 'LY':
                    codigo_pais = 602
                elif cls.party.address.country.code == 'DO':
                    codigo_pais = 122
                elif cls.party.address.country.code == 'DM':
                    codigo_pais = 136
                elif cls.party.address.country.code == 'DJ':
                    codigo_pais = 459
                elif cls.party.address.country.code == 'DK':
                    codigo_pais = 208
                elif cls.party.address.country.code == 'UM':
                    codigo_pais = 202
                elif cls.party.address.country.code == 'DE':
                    codigo_pais = 202
                elif cls.party.address.country.code == 'YE':
                    codigo_pais = 342
                elif cls.party.address.country.code == 'DZ':
                    codigo_pais = 403
                elif cls.party.address.country.code == 'UY':
                    codigo_pais = 125
                elif cls.party.address.country.code == 'YT':
                    codigo_pais = 443
                elif cls.party.address.country.code == 'VU':
                    codigo_pais = 516
                elif cls.party.address.country.code == 'QA':
                    codigo_pais =  334
                elif cls.party.address.country.code == 'TM':
                    codigo_pais = 351
                elif cls.party.address.country.code == 'EH':
                    codigo_pais = 447
                elif cls.party.address.country.code == 'WF':
                    codigo_pais = 532
                elif cls.party.address.country.code == 'EE':
                    codigo_pais = 245
                elif cls.party.address.country.code == 'EG':
                    codigo_pais = 434
                elif cls.party.address.country.code == 'ZA':
                    codigo_pais = 422
                elif cls.party.address.country.code == 'EC':
                    codigo_pais = 593
                elif cls.party.address.country.code == 'SJ':
                    codigo_pais = 110
                elif cls.party.address.country.code == 'US':
                    codigo_pais = 110
                elif cls.party.address.country.code == 'ET ':
                    codigo_pais = 407
                elif cls.party.address.country.code == 'ZW':
                    codigo_pais = 301
                elif cls.party.address.country.code == 'ES':
                    codigo_pais = 209
                elif cls.party.address.country.code == 'ER':
                    codigo_pais = 463
                elif cls.party.address.country.code == 'RU':
                    codigo_pais = 225
                elif cls.party.address.country.code == 'RW':
                    codigo_pais = 445
                elif cls.party.address.country.code == 'RS':
                    codigo_pais = 688
                elif cls.party.address.country.code == 'RE':
                    codigo_pais = 465
                elif cls.party.address.country.code == 'IT':
                    codigo_pais = 219
                elif cls.party.address.country.code == 'RO':
                    codigo_pais = 225
                elif cls.party.address.country.code == 'TK':
                    codigo_pais = 530
                elif cls.party.address.country.code == 'TZ':
                    codigo_pais = 425
                elif cls.party.address.country.code == 'BD':
                    codigo_pais = 328
                elif cls.party.address.country.code == 'BE':
                    codigo_pais = 204
                elif cls.party.address.country.code == 'BF':
                    codigo_pais = 402
                elif cls.party.address.country.code == 'BG':
                    codigo_pais = 205
                elif cls.party.address.country.code == 'VG':
                    codigo_pais = 146
                elif cls.party.address.country.code == 'BA':
                    codigo_pais = 242
                elif cls.party.address.country.code == 'BL':
                    codigo_pais = 590
                elif cls.party.address.country.code == 'BM':
                    codigo_pais = 142
                elif cls.party.address.country.code == 'BB':
                    codigo_pais = 130
                elif cls.party.address.country.code == 'BN':
                    codigo_pais = 344
                elif cls.party.address.country.code == 'BO':
                    codigo_pais = 102
                elif cls.party.address.country.code == 'BH':
                    codigo_pais = 327
                elif cls.party.address.country.code == 'BI':
                    codigo_pais = 404
                elif cls.party.address.country.code == 'BJ':
                    codigo_pais = 429
                elif cls.party.address.country.code == 'BT':
                    codigo_pais = 329
                elif cls.party.address.country.code == 'JM':
                    codigo_pais = 114
                elif cls.party.address.country.code == 'BV':
                    codigo_pais = 74
                elif cls.party.address.country.code == 'BW':
                    codigo_pais = 430
                elif cls.party.address.country.code == 'BQ':
                    codigo_pais = 103
                elif cls.party.address.country.code == 'BR':
                    codigo_pais = 103
                elif cls.party.address.country.code == 'BS':
                    codigo_pais = 129
                elif cls.party.address.country.code == 'JE':
                    codigo_pais = 499
                elif cls.party.address.country.code == 'BY':
                    codigo_pais = 596
                elif cls.party.address.country.code == 'BZ':
                    codigo_pais = 135
                elif cls.party.address.country.code == 'TN':
                    codigo_pais = 452
                elif cls.party.address.country.code == 'OM':
                    codigo_pais = 337
                elif cls.party.address.country.code == 'ZA':
                    codigo_pais = 427
                elif cls.party.address.country.code == 'UA':
                    codigo_pais = 229
                elif cls.party.address.country.code == 'JO':
                    codigo_pais = 315
                elif cls.party.address.country.code == 'MZ':
                    codigo_pais = 442
                elif cls.party.address.country.code == 'CK':
                    codigo_pais = 519
                elif cls.party.address.country.code == 'CI':
                    codigo_pais = 432
                elif cls.party.address.country.code == 'CH':
                    codigo_pais = 450
                elif cls.party.address.country.code == 'CO':
                    codigo_pais = 105
                elif cls.party.address.country.code == 'CN':
                    codigo_pais = 331
                elif cls.party.address.country.code == 'CM':
                    codigo_pais = 405
                elif cls.party.address.country.code == 'CL':
                    codigo_pais = 108
                elif cls.party.address.country.code == 'CC':
                    codigo_pais = 518
                elif cls.party.address.country.code == 'CA':
                    codigo_pais = 104
                elif cls.party.address.country.code == 'CG':
                    codigo_pais = 406
                elif cls.party.address.country.code == 'CF':
                    codigo_pais = 431
                elif cls.party.address.country.code == 'CD':
                    codigo_pais = 406
                elif cls.party.address.country.code == 'CZ':
                    codigo_pais = 599
                elif cls.party.address.country.code == 'CY':
                    codigo_pais = 332
                elif cls.party.address.country.code == 'CX':
                    codigo_pais = 520
                elif cls.party.address.country.code == 'CR':
                    codigo_pais = 106
                elif cls.party.address.country.code == 'CW':
                    codigo_pais = 127
                elif cls.party.address.country.code == 'CV':
                    codigo_pais = 456
                elif cls.party.address.country.code == 'CU':
                    codigo_pais = 107
                elif cls.party.address.country.code == 'VE':
                    codigo_pais = 126
                elif cls.party.address.country.code == 'PR':
                    codigo_pais = 121
                elif cls.party.address.country.code == 'PS':
                    codigo_pais = 353
                elif cls.party.address.country.code == 'SA':
                    codigo_pais = 302
                elif cls.party.address.country.code == 'PW':
                    codigo_pais = 509
                elif cls.party.address.country.code == 'PT':
                    codigo_pais = 224
                elif cls.party.address.country.code == 'PY':
                    codigo_pais = 119
                elif cls.party.address.country.code == 'TL':
                    codigo_pais = 529
                elif cls.party.address.country.code == 'IQ':
                    codigo_pais = 311
                elif cls.party.address.country.code == 'PA':
                    codigo_pais = 118
                elif cls.party.address.country.code == 'PF':
                    codigo_pais = 526
                elif cls.party.address.country.code == 'PG':
                    codigo_pais = 507
                elif cls.party.address.country.code == 'PE':
                    codigo_pais = 120
                elif cls.party.address.country.code == 'PK':
                    codigo_pais = 322
                elif cls.party.address.country.code == 'PH':
                    codigo_pais = 308
                elif cls.party.address.country.code == 'PN':
                    codigo_pais = 525
                elif cls.party.address.country.code == 'PL':
                    codigo_pais = 223
                elif cls.party.address.country.code == 'PM':
                    codigo_pais = 604
                elif cls.party.address.country.code == 'HR':
                    codigo_pais = 243
                elif cls.party.address.country.code == 'HT':
                    codigo_pais = 112
                elif cls.party.address.country.code == 'HU':
                    codigo_pais = 216
                elif cls.party.address.country.code == 'HK':
                    codigo_pais = 354
                elif cls.party.address.country.code == 'HN':
                    codigo_pais = 113
                elif cls.party.address.country.code == 'VN':
                    codigo_pais = 341
                elif cls.party.address.country.code == 'HM':
                    codigo_pais = 343
                elif cls.party.address.country.code == 'JP':
                    codigo_pais = 314
                elif cls.party.address.country.code == 'ME':
                    codigo_pais = 382
                elif cls.party.address.country.code == 'MD':
                    codigo_pais = 250
                elif cls.party.address.country.code == 'MG':
                    codigo_pais = 412
                elif cls.party.address.country.code == 'MF':
                    codigo_pais = 464
                elif cls.party.address.country.code == 'MA':
                    codigo_pais = 464
                elif cls.party.address.country.code == 'MC':
                    codigo_pais = 235
                elif cls.party.address.country.code == 'UZ':
                    codigo_pais = 352
                elif cls.party.address.country.code == 'ML':
                    codigo_pais = 414
                elif cls.party.address.country.code == 'MO':
                    codigo_pais = 355
                elif cls.party.address.country.code == 'MM':
                    codigo_pais = 303
                elif cls.party.address.country.code == 'MN':
                    codigo_pais = 321
                elif cls.party.address.country.code == 'MK':
                    codigo_pais = 251
                elif cls.party.address.country.code == 'MU':
                    codigo_pais = 441
                elif cls.party.address.country.code == 'MH':
                    codigo_pais = 511
                elif cls.party.address.country.code == 'MT':
                    codigo_pais = 221
                elif cls.party.address.country.code == 'MW':
                    codigo_pais = 413
                elif cls.party.address.country.code == 'MQ':
                    codigo_pais = 148
                elif cls.party.address.country.code == 'MV':
                    codigo_pais = 335
                elif cls.party.address.country.code == 'MP':
                    codigo_pais = 603
                elif cls.party.address.country.code == 'MS':
                    codigo_pais = 149
                elif cls.party.address.country.code == 'MR':
                    codigo_pais = 416
                elif cls.party.address.country.code == 'IM':
                    codigo_pais = 833
                elif cls.party.address.country.code == 'UG ':
                    codigo_pais = 426
                elif cls.party.address.country.code == 'MY':
                    codigo_pais = 319
                elif cls.party.address.country.code == 'MX':
                    codigo_pais = 116
                elif cls.party.address.country.code == 'IL':
                    codigo_pais = 313
                elif cls.party.address.country.code == 'VA':
                    codigo_pais = 139
                elif cls.party.address.country.code == 'VC':
                    codigo_pais = 139
                elif cls.party.address.country.code == 'AE':
                    codigo_pais = 333
                elif cls.party.address.country.code == 'AD':
                    codigo_pais = 233
                elif cls.party.address.country.code == 'AG':
                    codigo_pais = 134
                elif cls.party.address.country.code == 'AF':
                    codigo_pais = 109
                elif cls.party.address.country.code == 'AI':
                    codigo_pais = 109
                elif cls.party.address.country.code == 'VI':
                    codigo_pais = 146
                elif cls.party.address.country.code == 'IS':
                    codigo_pais = 218
                elif cls.party.address.country.code == 'IR':
                    codigo_pais = 312
                elif cls.party.address.country.code == 'AM':
                    codigo_pais = 356
                elif cls.party.address.country.code == 'AL':
                    codigo_pais = 201
                elif cls.party.address.country.code == 'AO':
                    codigo_pais = 454
                elif cls.party.address.country.code == 'KN':
                    codigo_pais = 137
                elif cls.party.address.country.code == 'AQ':
                    codigo_pais = 606
                elif cls.party.address.country.code == 'AS':
                    codigo_pais = 16
                elif cls.party.address.country.code == 'AR':
                    codigo_pais = 101
                elif cls.party.address.country.code == 'AU':
                    codigo_pais = 501
                elif cls.party.address.country.code == 'AT':
                    codigo_pais = 203
                elif cls.party.address.country.code == 'AW':
                    codigo_pais = 141
                elif cls.party.address.country.code == 'IN':
                    codigo_pais = 309
                elif cls.party.address.country.code == 'AX':
                    codigo_pais = 428
                elif cls.party.address.country.code == 'AZ':
                    codigo_pais = 347
                elif cls.party.address.country.code == 'IE':
                    codigo_pais = 217
                elif cls.party.address.country.code == 'ID':
                    codigo_pais = 310
                elif cls.party.address.country.code == 'NI':
                    codigo_pais = 117
                elif cls.party.address.country.code == 'NL':
                    codigo_pais = 215
                elif cls.party.address.country.code == 'NO':
                    codigo_pais = 222
                elif cls.party.address.country.code == 'NA':
                    codigo_pais = 460
                elif cls.party.address.country.code == 'NC':
                    codigo_pais = 524
                elif cls.party.address.country.code == 'NE':
                    codigo_pais = 444
                elif cls.party.address.country.code == 'NF':
                    codigo_pais = 523
                elif cls.party.address.country.code == 'NG':
                    codigo_pais = 417
                elif cls.party.address.country.code == 'NZ':
                    codigo_pais = 503
                elif cls.party.address.country.code == 'SH':
                    codigo_pais = 466
                elif cls.party.address.country.code == 'NP':
                    codigo_pais = 336
                elif cls.party.address.country.code == 'SO':
                    codigo_pais = 448
                elif cls.party.address.country.code == 'NR':
                    codigo_pais = 513
                elif cls.party.address.country.code == 'NU':
                    codigo_pais = 522
                elif cls.party.address.country.code == 'FR':
                    codigo_pais = 211
                elif cls.party.address.country.code == 'IO':
                    codigo_pais = 607
                elif cls.party.address.country.code == 'SB':
                    codigo_pais = 514
                elif cls.party.address.country.code == 'FI':
                    codigo_pais = 212
                elif cls.party.address.country.code == 'FJ':
                    codigo_pais = 506
                elif cls.party.address.country.code == 'FK':
                    codigo_pais = 115
                elif cls.party.address.country.code == 'FM':
                    codigo_pais = 512
                elif cls.party.address.country.code == 'FO':
                    codigo_pais = 253
                elif cls.party.address.country.code == 'TJ':
                    codigo_pais = 350
                elif cls.party.address.country.code == 'SZ':
                    codigo_pais = 148
                elif cls.party.address.country.code == 'SY':
                    codigo_pais = 605
                elif cls.party.address.country.code == 'SX':
                    codigo_pais = 349
                elif cls.party.address.country.code == 'KG':
                    codigo_pais = 349
                elif cls.party.address.country.code == 'KE':
                    codigo_pais = 439
                elif cls.party.address.country.code == 'SS':
                    codigo_pais = 421
                elif cls.party.address.country.code == 'SR':
                    codigo_pais = 133
                elif cls.party.address.country.code == 'KI':
                    codigo_pais = 510
                elif cls.party.address.country.code == 'KH':
                    codigo_pais = 304
                elif cls.party.address.country.code == 'SV':
                    codigo_pais = 123
                elif cls.party.address.country.code == 'KM':
                    codigo_pais = 458
                elif cls.party.address.country.code == 'ST':
                    codigo_pais = 449
                elif cls.party.address.country.code == 'SK':
                    codigo_pais = 252
                elif cls.party.address.country.code == 'KR':
                    codigo_pais = 330
                elif cls.party.address.country.code == 'SI':
                    codigo_pais = 344
                elif cls.party.address.country.code == 'KP':
                    codigo_pais = 306
                elif cls.party.address.country.code == 'KW':
                    codigo_pais = 316
                elif cls.party.address.country.code == 'SN':
                    codigo_pais = 420
                elif cls.party.address.country.code == 'SM':
                    codigo_pais = 237
                elif cls.party.address.country.code == 'SL':
                    codigo_pais = 423
                elif cls.party.address.country.code == 'SC':
                    codigo_pais = 446
                elif cls.party.address.country.code == 'KY':
                    codigo_pais = 348
                elif cls.party.address.country.code == 'KY':
                    codigo_pais = 145
                elif cls.party.address.country.code == 'SE':
                    codigo_pais = 226
                elif cls.party.address.country.code == 'SG':
                    codigo_pais = 338
                elif cls.party.address.country.code == 'SD':
                    codigo_pais = 421
                etree.SubElement(pagoExterior, 'paisEfecPago').text = codigo_pais
            etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = cls.party.convenio_doble
            etree.SubElement(pagoExterior, 'pagExtSujRetNorLeg').text = cls.party.sujeto_retencion
            etree.SubElement(pagoExterior, 'pagoRegFis').text = cls.party.pago_regimen
            detallecompras.append(pagoExterior)
            if formas_de_pago:
                formasDePago = etree.Element('formasDePago')
                etree.SubElement(formasDePago, 'formaPago').text = inv.formas_de_pago
                detallecompras.append(formasDePago)
                
            air = etree.Element('air')
            detalleAir = etree.Element('detalleAir')
            etree.SubElement(detalleAir, 'codRetAir').text = inv.impuestos_ats_renta.code
            etree.SubElement(detalleAir, 'baseImpAir').text = '{:.2f}'.format(inv.untaxed_amount)
            etree.SubElement(detalleAir, 'porcentajeAir').text = inv.impuestos_ats_renta.rate
            etree.SubElement(detalleAir, 'valRetAir').text = '{:.2f}'.format((inv.impuestos_ats_renta.rate)*(inv.untaxed_amount))
            if inv.impuestos_ats_renta.code == '345' | inv.impuestos_ats_renta.code == '345A' | inv.impuestos_ats_renta.code ==  '346':
                etree.SubElement(detalleAir, 'fechaPagoDiv').text = inv.invoice_date.strftime('%d/%m/%Y')
            if inv.impuestos_ats_renta.code == '327' | inv.impuestos_ats_renta.code=='330' | inv.impuestos_ats_renta.code=='504' | inv.impuestos_ats_renta.code=='504D':
                etree.SubElement(detalleAir, 'imRentaSoc').text = '000' #pendiente
                etree.SubElement(detalleAir, 'anioUtDiv').text = '000' #pendiente
            air.append(detalleAir)
            detallecompras.append(air)
            etree.SubElement(detallecompras, 'estabRetencion1').text = '000' #pendiente
            etree.SubElement(detallecompras, 'ptoEmiRetencion1').text = '000' #pendiente
            etree.SubElement(detallecompras, 'secRetencion1').text = '000' #pendiente
            etree.SubElement(detallecompras, 'autRetencion1').text = '000' #pendiente
            etree.SubElement(detallecompras, 'fechaEmiRet1').text = '000' #pendiente
            etree.SubElement(detallecompras, 'docModificado').text = '0'
            etree.SubElement(detallecompras, 'estabModificado').text = '000'
            etree.SubElement(detallecompras, 'ptoEmiModificado').text = '000'
            etree.SubElement(detallecompras, 'secModificado').text = '0'
            etree.SubElement(detallecompras, 'autModificado').text = '0000'
            compras.append(detallecompras)
        ats.append(compras)
        invoices_out = Invoice.search([('state','in',['posted','paid']), ('type','=','out_invoice')])
        partys = Party.search([('active', '=','true')])
        invoice_line = InvoiceLine.search([('invoice','!=','')])
        numeroComprobantes = 0     
        base_parcial = 0
        base_imponible = 0
        montoIva = 0
        ventas_establecimiento = 0
        baseImponible = 0
        
        ventas = etree.Element('ventas')
        for party in partys:
            print "El tercero ", party
            detalleVentas = etree.Element('detalleVentas')
            etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.SubElement(detalleVentas, 'parteRelVtas').text = party.parte_relacional
            for inv_out in invoices_out:
                for i_line in invoice_line:
                    if i_line.invoice == inv_out.id and i_line.party == party.id:
                        etree.SubElement(detalleVentas, 'tipoComprobante').text = tipoDocumento[inv_out.type]
                        numeroComprobantes = numeroComprobantes + 1
                        base_parcial = (i_line.unit_price)*(i_line.quantity)
                        baseImponible = base_parcial + base_imponible
                        montoIva = (baseImponible * (12))/100
            print "El numero de comprobante", numeroComprobantes
            etree.SubElement(detalleVentas, 'numeroComprobantes').text = str(numeroComprobantes)
            etree.SubElement(detalleVentas, 'baseNoGraIva').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'baseImponible').text = str(baseImponible)
            etree.SubElement(detalleVentas, 'baseImpGrav').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'montoIva').text = str(montoIva)
            etree.SubElement(detalleVentas, 'valorRetIva').text = '000' #pendiente
            etree.SubElement(detalleVentas, 'valorRetRenta').text = '000' #pendiente
            ventas.append(detalleVentas)
            ats.append(ventas)
            ventas_establecimiento = baseImponible + ventas_establecimiento 
                            
        """ Ventas establecimiento """
        ventasEstablecimiento = etree.Element('ventasEstablecimiento')
        ventaEst = etree.Element('ventaEst')
        etree.SubElement(ventaEst, 'codEstab').text = '000' #pendiente
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
        MESSAGE_INVALID = u'El sistema genero el XML pero los datos no pasan la validacion XSD del SRI. Revise el error: \n %s'
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
    "Export translation"
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
        file_data = Account.generate_ats()
        cls.result.file = buffer(file_data) if file_data else None
        return 'result'

    def default_result(cls, fields):
        file_ = cls.result.file
        cls.result.file = False  # No need to store it in session
        return {
            'file': file_,
            }
            

