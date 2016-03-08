import time
import base64
import StringIO
from lxml import etree
from lxml.etree import DocumentInvalid
import datetime

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

class ATS():

    _name = 'ats'

    def _get_ret_iva(self, invoice):
        """
        Return (valorRetServicios, valorRetServ100)
        """
        retServ = 0
        retServ100 = 0
        for tax in invoice.tax_line:
            if tax.tax_group == 'ret_vat_srv':
                if tax.percent == '100':
                    retServ100 += abs(tax.tax_amount)
                else:
                    retServ += abs(tax.tax_amount)
        return retServ, retServ100

    def generate_ats(self):
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
        
        ats = etree.Element('iva')
        etree.SubElement(ats, 'TipoIdInformante').text = 'R'
        etree.SubElement(ats, 'IdInformante').text = self.company.party.vat_number
        etree.SubElement(ats, 'razonSocial').text = self.company.party.name
        period = Period.browse([(period_id)])[0]
        etree.SubElement(ats, 'Anio').text = time.strftime(period.date_start, '%Y')
        etree.SubElement(ats, 'Mes').text = time.strftime(period.date_start, '%m')        
        #numero de establecimientos del emisor->entero
        etree.SubElement(ats, 'numEstabRuc').text = 003
        total_ventas = self._get_ventas(period_id)
        etree.SubElement(ats, 'totalVentas').text = self.get_ventas
        etree.SubElement(ats, 'codigoOperativo').text = 'IVA'
        compras = etree.Element('compras')
        
        invoices = Invoice.search([('state','in',['posted','paid']), ('type','=','in_invoice')])
      
        for inv in invoices:
            detallecompras = etree.Element('detalleCompras')
            #pendiente codigo de sustento
            etree.SubElement(detallecompras, 'codSustento').text = self.party.type_sustent
            etree.SubElement(detallecompras, 'tpIdProv').text = tipoIdentificacion[self.party.type_document]
            etree.SubElement(detallecompras, 'idProv').text = self.party.vat_number
            etree.SubElement(detallecompras, 'tipoComprobante').text = tipoDocumento[self.type]
            if tipoIdentificacion[self.party.type_document] == '03':
                etree.SubElement(detallecompras, 'tipoProv').text = tipoProvedor[self.party.type_party]
            etree.SubElement(detallecompras, 'parteRel').text = self.party.parte_relacional
            etree.SubElement(detallecompras, 'fechaRegistro').text = time.strftime(inv.date_invoice, '%d/%m/%Y')
            etree.SubElement(detallecompras, 'establecimiento').text = '001'
            etree.SubElement(detallecompras, 'puntoEmision').text = '001'
            etree.SubElement(detallecompras, 'secuencial').text = inv.number
            etree.SubElement(detallecompras, 'fechaEmision').text = time.strftime(inv.date_invoice, '%d/%m/%Y')
            etree.SubElement(detallecompras, 'autorizacion').text = inv.numero_autorizacion
            etree.SubElement(detallecompras, 'baseNoGraIva').text = 
            etree.SubElement(detallecompras, 'baseImponible').text = 
            etree.SubElement(detallecompras, 'baseImpGrav').text = '%.2f'%inv.untaxed_amount
            etree.SubElement(detallecompras, 'montoIce').text = '0.00'
            etree.SubElement(detallecompras, 'montoIva').text = '%.2f'%inv.tax_amount
            etree.SubElement(detallecompras, 'valorRetBienes').text = '%.2f'%abs(inv. )
            
            etree.SubElement(detallecompras, 'valorRetServicios').text = '%.2f'%
            etree.SubElement(detallecompras, 'valRetServ100').text = '%.2f'%
            pagoExterior = etree.Element('pagoExterior')
            etree.SubElement(pagoExterior, 'pagoLocExt').text = self.party.tipo_de_pago
            if self.party.tipo_de_pago == '02':
                if self.party.address.country.code == 'GW':
                    codigo_pais = 437
                elif self.party.address.country.code == 'GU':
                    codigo_pais = 517
                elif self.party.address.country.code == 'GT':
                    codigo_pais = 111
                elif self.party.address.country.code == 'GS':
                    codigo_pais = 246
                elif self.party.address.country.code == 'GR':
                    codigo_pais = 214
                elif self.party.address.country.code == 'GQ':
                    codigo_pais = 438
                elif self.party.address.country.code == 'GP':
                    codigo_pais = 143
                elif self.party.address.country.code == 'GY':
                    codigo_pais = 132
                elif self.party.address.country.code == 'GG':
                    codigo_pais = 831
                elif self.party.address.country.code == 'GF':
                    codigo_pais = 144
                elif self.party.address.country.code == 'GE':
                    codigo_pais = 246
                elif self.party.address.country.code == 'GD':
                    codigo_pais = 131
                elif self.party.address.country.code == 'GB':
                    codigo_pais = 213
                elif self.party.address.country.code == 'GA':
                    codigo_pais = 435
                elif self.party.address.country.code == 'GN':
                    codigo_pais = 409
                elif self.party.address.country.code == 'GM':
                    codigo_pais = 408
                elif self.party.address.country.code == 'GL':
                    codigo_pais = 247
                elif self.party.address.country.code == 'GI':
                    codigo_pais = 239
                elif self.party.address.country.code == 'GH':
                    codigo_pais = 436
                elif self.party.address.country.code == 'LC':
                    codigo_pais = 138
                elif self.party.address.country.code == 'LB':
                    codigo_pais = 318
                elif self.party.address.country.code == 'LA':
                    codigo_pais = 122
                elif self.party.address.country.code == 'TV':
                    codigo_pais = 515
                elif self.party.address.country.code == 'TW':
                    codigo_pais = 307
                elif self.party.address.country.code == 'TT':
                    codigo_pais = 124
                elif self.party.address.country.code == 'TR':
                    codigo_pais = 346
                elif self.party.address.country.code == 'LK':
                    codigo_pais = 339
                elif self.party.address.country.code == 'LI':
                    codigo_pais = 234
                elif self.party.address.country.code == 'LV':
                    codigo_pais = 601
                elif self.party.address.country.code == 'TO':
                    codigo_pais = 508
                elif self.party.address.country.code == 'LT':
                    codigo_pais = 249
                elif self.party.address.country.code == 'LU':
                    codigo_pais = 220
                elif self.party.address.country.code == 'LR':
                    codigo_pais = 410
                elif self.party.address.country.code == 'LS':
                    codigo_pais = 440
                elif self.party.address.country.code == 'TH':
                    codigo_pais = 325
                elif self.party.address.country.code == 'TF':
                    codigo_pais = 260
                elif self.party.address.country.code == 'TG':
                    codigo_pais = 451
                elif self.party.address.country.code == 'TD':
                    codigo_pais = 433
                elif self.party.address.country.code == 'TC':
                    codigo_pais = 151
                elif self.party.address.country.code == 'LY':
                    codigo_pais = 602
                elif self.party.address.country.code == 'DO':
                    codigo_pais = 122
                elif self.party.address.country.code == 'DM':
                    codigo_pais = 136
                elif self.party.address.country.code == 'DJ':
                    codigo_pais = 459
                elif self.party.address.country.code == 'DK':
                    codigo_pais = 208
                elif self.party.address.country.code == 'UM':
                    codigo_pais = 202
                elif self.party.address.country.code == 'DE':
                    codigo_pais = 202
                elif self.party.address.country.code == 'YE':
                    codigo_pais = 342
                elif self.party.address.country.code == 'DZ':
                    codigo_pais = 403
                elif self.party.address.country.code == 'UY':
                    codigo_pais = 125
                elif self.party.address.country.code == 'YT':
                    codigo_pais = 443
                elif self.party.address.country.code == 'VU':
                    codigo_pais = 516
                elif self.party.address.country.code == 'QA':
                    codigo_pais =  334
                elif self.party.address.country.code == 'TM':
                    codigo_pais = 351
                elif self.party.address.country.code == 'EH':
                    codigo_pais = 447
                elif self.party.address.country.code == 'WF':
                    codigo_pais = 532
                elif self.party.address.country.code == 'EE':
                    codigo_pais = 245
                elif self.party.address.country.code == 'EG':
                    codigo_pais = 434
                elif self.party.address.country.code == 'ZA':
                    codigo_pais = 422
                elif self.party.address.country.code == 'EC':
                    codigo_pais = 593
                elif self.party.address.country.code == 'SJ':
                    codigo_pais = 110
                elif self.party.address.country.code == 'US':
                    codigo_pais = 110
                elif self.party.address.country.code == 'ET ':
                    codigo_pais = 407
                elif self.party.address.country.code == 'ZW':
                    codigo_pais = 301
                elif self.party.address.country.code == 'ES':
                    codigo_pais = 209
                elif self.party.address.country.code == 'ER':
                    codigo_pais = 463
                elif self.party.address.country.code == 'RU':
                    codigo_pais = 225
                elif self.party.address.country.code == 'RW':
                    codigo_pais = 445
                elif self.party.address.country.code == 'RS':
                    codigo_pais = 688
                elif self.party.address.country.code == 'RE':
                    codigo_pais = 465
                elif self.party.address.country.code == 'IT':
                    codigo_pais = 219
                elif self.party.address.country.code == 'RO':
                    codigo_pais = 225
                elif self.party.address.country.code == 'TK':
                    codigo_pais = 530
                elif self.party.address.country.code == 'TZ':
                    codigo_pais = 425
                elif self.party.address.country.code == 'BD':
                    codigo_pais = 328
                elif self.party.address.country.code == 'BE':
                    codigo_pais = 204
                elif self.party.address.country.code == 'BF':
                    codigo_pais = 402
                elif self.party.address.country.code == 'BG':
                    codigo_pais = 205
                elif self.party.address.country.code == 'VG':
                    codigo_pais = 146
                elif self.party.address.country.code == 'BA':
                    codigo_pais = 242
                elif self.party.address.country.code == 'BL':
                    codigo_pais = 590
                elif self.party.address.country.code == 'BM':
                    codigo_pais = 142
                elif self.party.address.country.code == 'BB':
                    codigo_pais = 130
                elif self.party.address.country.code == 'BN':
                    codigo_pais = 344
                elif self.party.address.country.code == 'BO':
                    codigo_pais = 102
                elif self.party.address.country.code == 'BH':
                    codigo_pais = 327
                elif self.party.address.country.code == 'BI':
                    codigo_pais = 404
                elif self.party.address.country.code == 'BJ':
                    codigo_pais = 429
                elif self.party.address.country.code == 'BT':
                    codigo_pais = 329
                elif self.party.address.country.code == 'JM':
                    codigo_pais = 114
                elif self.party.address.country.code == 'BV':
                    codigo_pais = 74
                elif self.party.address.country.code == 'BW':
                    codigo_pais = 430
                elif self.party.address.country.code == 'BQ':
                    codigo_pais = 103
                elif self.party.address.country.code == 'BR':
                    codigo_pais = 103
                elif self.party.address.country.code == 'BS':
                    codigo_pais = 129
                elif self.party.address.country.code == 'JE':
                    codigo_pais = 499
                elif self.party.address.country.code == 'BY':
                    codigo_pais = 596
                elif self.party.address.country.code == 'BZ':
                    codigo_pais = 135
                elif self.party.address.country.code == 'TN':
                    codigo_pais = 452
                elif self.party.address.country.code == 'OM':
                    codigo_pais = 337
                elif self.party.address.country.code == 'ZA':
                    codigo_pais = 427
                elif self.party.address.country.code == 'UA':
                    codigo_pais = 229
                elif self.party.address.country.code == 'JO':
                    codigo_pais = 315
                elif self.party.address.country.code == 'MZ':
                    codigo_pais = 442
                elif self.party.address.country.code == 'CK':
                    codigo_pais = 519
                elif self.party.address.country.code == 'CI':
                    codigo_pais = 432
                elif self.party.address.country.code == 'CH':
                    codigo_pais = 450
                elif self.party.address.country.code == 'CO':
                    codigo_pais = 105
                elif self.party.address.country.code == 'CN':
                    codigo_pais = 331
                elif self.party.address.country.code == 'CM':
                    codigo_pais = 405
                elif self.party.address.country.code == 'CL':
                    codigo_pais = 108
                elif self.party.address.country.code == 'CC':
                    codigo_pais = 518
                elif self.party.address.country.code == 'CA':
                    codigo_pais = 104
                elif self.party.address.country.code == 'CG':
                    codigo_pais = 406
                elif self.party.address.country.code == 'CF':
                    codigo_pais = 431
                elif self.party.address.country.code == 'CD':
                    codigo_pais = 406
                elif self.party.address.country.code == 'CZ':
                    codigo_pais = 599
                elif self.party.address.country.code == 'CY':
                    codigo_pais = 332
                elif self.party.address.country.code == 'CX':
                    codigo_pais = 520
                elif self.party.address.country.code == 'CR':
                    codigo_pais = 106
                elif self.party.address.country.code == 'CW':
                    codigo_pais = 127
                elif self.party.address.country.code == 'CV':
                    codigo_pais = 456
                elif self.party.address.country.code == 'CU':
                    codigo_pais = 107
                elif self.party.address.country.code == 'VE':
                    codigo_pais = 126
                elif self.party.address.country.code == 'PR':
                    codigo_pais = 121
                elif self.party.address.country.code == 'PS':
                    codigo_pais = 353
                elif self.party.address.country.code == 'SA':
                    codigo_pais = 302
                elif self.party.address.country.code == 'PW':
                    codigo_pais = 509
                elif self.party.address.country.code == 'PT':
                    codigo_pais = 224
                elif self.party.address.country.code == 'PY':
                    codigo_pais = 119
                elif self.party.address.country.code == 'TL':
                    codigo_pais = 529
                elif self.party.address.country.code == 'IQ':
                    codigo_pais = 311
                elif self.party.address.country.code == 'PA':
                    codigo_pais = 118
                elif self.party.address.country.code == 'PF':
                    codigo_pais = 526
                elif self.party.address.country.code == 'PG':
                    codigo_pais = 507
                elif self.party.address.country.code == 'PE':
                    codigo_pais = 120
                elif self.party.address.country.code == 'PK':
                    codigo_pais = 322
                elif self.party.address.country.code == 'PH':
                    codigo_pais = 308
                elif self.party.address.country.code == 'PN':
                    codigo_pais = 525
                elif self.party.address.country.code == 'PL':
                    codigo_pais = 223
                elif self.party.address.country.code == 'PM':
                    codigo_pais = 604
                elif self.party.address.country.code == 'HR':
                    codigo_pais = 243
                elif self.party.address.country.code == 'HT':
                    codigo_pais = 112
                elif self.party.address.country.code == 'HU':
                    codigo_pais = 216
                elif self.party.address.country.code == 'HK':
                    codigo_pais = 354
                elif self.party.address.country.code == 'HN':
                    codigo_pais = 113
                elif self.party.address.country.code == 'VN':
                    codigo_pais = 341
                elif self.party.address.country.code == 'HM':
                    codigo_pais = 343
                elif self.party.address.country.code == 'JP':
                    codigo_pais = 314
                elif self.party.address.country.code == 'ME':
                    codigo_pais = 382
                elif self.party.address.country.code == 'MD':
                    codigo_pais = 250
                elif self.party.address.country.code == 'MG':
                    codigo_pais = 412
                elif self.party.address.country.code == 'MF':
                    codigo_pais = 464
                elif self.party.address.country.code == 'MA':
                    codigo_pais = 464
                elif self.party.address.country.code == 'MC':
                    codigo_pais = 235
                elif self.party.address.country.code == 'UZ':
                    codigo_pais = 352
                elif self.party.address.country.code == 'ML':
                    codigo_pais = 414
                elif self.party.address.country.code == 'MO':
                    codigo_pais = 355
                elif self.party.address.country.code == 'MM':
                    codigo_pais = 303
                elif self.party.address.country.code == 'MN':
                    codigo_pais = 321
                elif self.party.address.country.code == 'MK':
                    codigo_pais = 251
                elif self.party.address.country.code == 'MU':
                    codigo_pais = 441
                elif self.party.address.country.code == 'MH':
                    codigo_pais = 511
                elif self.party.address.country.code == 'MT':
                    codigo_pais = 221
                elif self.party.address.country.code == 'MW':
                    codigo_pais = 413
                elif self.party.address.country.code == 'MQ':
                    codigo_pais = 148
                elif self.party.address.country.code == 'MV':
                    codigo_pais = 335
                elif self.party.address.country.code == 'MP':
                    codigo_pais = 603
                elif self.party.address.country.code == 'MS':
                    codigo_pais = 149
                elif self.party.address.country.code == 'MR':
                    codigo_pais = 416
                elif self.party.address.country.code == 'IM':
                    codigo_pais = 833
                elif self.party.address.country.code == 'UG ':
                    codigo_pais = 426
                elif self.party.address.country.code == 'MY':
                    codigo_pais = 319
                elif self.party.address.country.code == 'MX':
                    codigo_pais = 116
                elif self.party.address.country.code == 'IL':
                    codigo_pais = 313
                elif self.party.address.country.code == 'VA':
                    codigo_pais = 139
                elif self.party.address.country.code == 'VC':
                    codigo_pais = 139
                elif self.party.address.country.code == 'AE':
                    codigo_pais = 333
                elif self.party.address.country.code == 'AD':
                    codigo_pais = 233
                elif self.party.address.country.code == 'AG':
                    codigo_pais = 134
                elif self.party.address.country.code == 'AF':
                    codigo_pais = 109
                elif self.party.address.country.code == 'AI':
                    codigo_pais = 109
                elif self.party.address.country.code == 'VI':
                    codigo_pais = 146
                elif self.party.address.country.code == 'IS':
                    codigo_pais = 218
                elif self.party.address.country.code == 'IR':
                    codigo_pais = 312
                elif self.party.address.country.code == 'AM':
                    codigo_pais = 356
                elif self.party.address.country.code == 'AL':
                    codigo_pais = 201
                elif self.party.address.country.code == 'AO':
                    codigo_pais = 454
                elif self.party.address.country.code == 'KN':
                    codigo_pais = 137
                elif self.party.address.country.code == 'AQ':
                    codigo_pais = 606
                elif self.party.address.country.code == 'AS':
                    codigo_pais = 16
                elif self.party.address.country.code == 'AR':
                    codigo_pais = 101
                elif self.party.address.country.code == 'AU':
                    codigo_pais = 501
                elif self.party.address.country.code == 'AT':
                    codigo_pais = 203
                elif self.party.address.country.code == 'AW':
                    codigo_pais = 141
                elif self.party.address.country.code == 'IN':
                    codigo_pais = 309
                elif self.party.address.country.code == 'AX':
                    codigo_pais = 428
                elif self.party.address.country.code == 'AZ':
                    codigo_pais = 347
                elif self.party.address.country.code == 'IE':
                    codigo_pais = 217
                elif self.party.address.country.code == 'ID':
                    codigo_pais = 310
                elif self.party.address.country.code == 'NI':
                    codigo_pais = 117
                elif self.party.address.country.code == 'NL':
                    codigo_pais = 215
                elif self.party.address.country.code == 'NO':
                    codigo_pais = 222
                elif self.party.address.country.code == 'NA':
                    codigo_pais = 460
                elif self.party.address.country.code == 'NC':
                    codigo_pais = 524
                elif self.party.address.country.code == 'NE':
                    codigo_pais = 444
                elif self.party.address.country.code == 'NF':
                    codigo_pais = 523
                elif self.party.address.country.code == 'NG':
                    codigo_pais = 417
                elif self.party.address.country.code == 'NZ':
                    codigo_pais = 503
                elif self.party.address.country.code == 'SH':
                    codigo_pais = 466
                elif self.party.address.country.code == 'NP':
                    codigo_pais = 336
                elif self.party.address.country.code == 'SO':
                    codigo_pais = 448
                elif self.party.address.country.code == 'NR':
                    codigo_pais = 513
                elif self.party.address.country.code == 'NU':
                    codigo_pais = 522
                elif self.party.address.country.code == 'FR':
                    codigo_pais = 211
                elif self.party.address.country.code == 'IO':
                    codigo_pais = 607
                elif self.party.address.country.code == 'SB':
                    codigo_pais = 514
                elif self.party.address.country.code == 'FI':
                    codigo_pais = 212
                elif self.party.address.country.code == 'FJ':
                    codigo_pais = 506
                elif self.party.address.country.code == 'FK':
                    codigo_pais = 115
                elif self.party.address.country.code == 'FM':
                    codigo_pais = 512
                elif self.party.address.country.code == 'FO':
                    codigo_pais = 253
                elif self.party.address.country.code == 'TJ':
                    codigo_pais = 350
                elif self.party.address.country.code == 'SZ':
                    codigo_pais = 148
                elif self.party.address.country.code == 'SY':
                    codigo_pais = 605
                elif self.party.address.country.code == 'SX':
                    codigo_pais = 349
                elif self.party.address.country.code == 'KG':
                    codigo_pais = 349
                elif self.party.address.country.code == 'KE':
                    codigo_pais = 439
                elif self.party.address.country.code == 'SS':
                    codigo_pais = 421
                elif self.party.address.country.code == 'SR':
                    codigo_pais = 133
                elif self.party.address.country.code == 'KI':
                    codigo_pais = 510
                elif self.party.address.country.code == 'KH':
                    codigo_pais = 304
                elif self.party.address.country.code == 'SV':
                    codigo_pais = 123
                elif self.party.address.country.code == 'KM':
                    codigo_pais = 458
                elif self.party.address.country.code == 'ST':
                    codigo_pais = 449
                elif self.party.address.country.code == 'SK':
                    codigo_pais = 252
                elif self.party.address.country.code == 'KR':
                    codigo_pais = 330
                elif self.party.address.country.code == 'SI':
                    codigo_pais = 344
                elif self.party.address.country.code == 'KP':
                    codigo_pais = 306
                elif self.party.address.country.code == 'KW':
                    codigo_pais = 316
                elif self.party.address.country.code == 'SN':
                    codigo_pais = 420
                elif self.party.address.country.code == 'SM':
                    codigo_pais = 237
                elif self.party.address.country.code == 'SL':
                    codigo_pais = 423
                elif self.party.address.country.code == 'SC':
                    codigo_pais = 446
                elif self.party.address.country.code == 'KY':
                    codigo_pais = 348
                elif self.party.address.country.code == 'KY':
                    codigo_pais = 145
                elif self.party.address.country.code == 'SE':
                    codigo_pais = 226
                elif self.party.address.country.code == 'SG':
                    codigo_pais = 338
                elif self.party.address.country.code == 'SD':
                    codigo_pais = 421
                etree.SubElement(pagoExterior, 'paisEfecPago').text = codigo_pais
            etree.SubElement(pagoExterior, 'aplicConvDobTrib').text = self.party.convenio_doble
            etree.SubElement(pagoExterior, 'pagExtSujRetNorLeg').text = self.party.sujeto_retencion
            etree.SubElement(pagoExterior, 'pagoRegFis').text = self.party.pago_regimen
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
            if inv.impuestos_ats_renta.code == '345' | inv.impuestos_ats_renta.code == '345A' | inv.impuestos_ats_renta.code ==  '346'
                etree.SubElement(detalleAir, 'fechaPagoDiv').text = inv.invoice_date.strftime('%d/%m/%Y')
            if inv.impuestos_ats_renta.code == '327' | inv.impuestos_ats_renta.code=='330' | inv.impuestos_ats_renta.code=='504' | inv.impuestos_ats_renta.code=='504D'
                etree.SubElement(detalleAir, 'imRentaSoc').text = #pendiente
                etree.SubElement(detalleAir, 'anioUtDiv').text = #pendiente
            air.append(detalleAir)
            detallecompras.append(air)
            etree.SubElement(detallecompras, 'estabRetencion1').text = 
            etree.SubElement(detallecompras, 'ptoEmiRetencion1').text =
            etree.SubElement(detallecompras, 'secRetencion1').text = 
            etree.SubElement(detallecompras, 'autRetencion1').text = 
            etree.SubElement(detallecompras, 'fechaEmiRet1').text = 
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
        for party in partys:
            detalleVentas = etree.Element('detalleVentas')
            etree.SubElement(detalleVentas, 'tpIdCliente').text = identificacionCliente[party.type_document]
            etree.SubElement(detalleVentas, 'idCliente').text = party.vat_number
            etree.subElement(detalleVentas, 'parteRel').text = party.parte_relacional
            etree.SubElement(detalleVentas, 'tipoComprobante').text = tipoDocumento[party.type]
            for inv_out in invoices_out:
                for i_line in invoice_line:
                    if i_line.invoice == inv_out.id and i_line.party == party.id:
                        numeroComprobantes = numeroComprobantes + 1
                        base_parcial = (i_line.unit_price)*(i_line.quantity)
                        baseImponible = base_parcial + base_imponible
                        montoIva = (baseImponible * (12))/100

            etree.SubElement(detalleVentas, 'numeroComprobantes').text = numeroComprobantes
            etree.SubElement(detalleVentas, 'baseNoGraIva').text = 
            etree.SubElement(detalleVentas, 'baseImponible').text = baseImponible
            etree.SubElement(detalleVentas, 'baseImpGrav').text = 
            etree.SubElement(detalleVentas, 'montoIva').text = montoIva
            etree.SubElement(detalleVentas, 'valorRetIva').text = 
            etree.Subelement(detalleVentas, 'valorRetRenta').text = 
            ventas.append(detalleVentas)
            ats.append(ventas)
            ventas_establecimiento = baseImponible + ventas_establicimiento 
                            
        """ Ventas establecimiento """
        ventasEstablecimiento = etree.Element('ventasEstablecimiento')
        ventaEst = etree.Element('ventaEst')
        etree.SubElement(ventaEst, 'codEstab').text =
        etree.SubElement(ventaEst, 'ventasEstab').text = 
        ventasEstablecimiento.append(ventaEst)
        ats.append(ventasEstablecimiento)
        """Documentos Anulados"""
        anulados = etree.Element('anulados')
        inv_ids = inv_obj.search([('state','=','cancel'),
                                  ('period_id','=',period_id),
                                  ('type','=','out_invoice'),
                                  ('company_id','=',company_id.id)])
                                  
       
        for inv in inv_obj:
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
        MESSAGE_INVALID = u'El sistema generó el XML pero los datos no pasan la validación XSD del SRI. Revise el error: \n %s'
        file_path = os.path.join(os.path.dirname(__file__), 'ats.xsd')
        schema_file = open(file_path)
        file_ats = etree.tostring(ats, pretty_print=True, encoding='iso-8859-1')
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        
        try:
            xmlschema.assertValid(ats)
        except DocumentInvalid as e:
            print e
            self.raise_user_error(MESSAGE_INVALID, str(e))
                
        buf = StringIO.StringIO()
        buf.write(file_ats)
        out=base64.encodestring(buf.getvalue())
        buf.close()
        name = "%s%s%s.XML" % ("AT", period_id.name[:2], period_id.name[3:8])
        return self.write({'state': 'export', 'data': out, 'name': name})

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
               
    
class OpenAnnexTransactionalSimplifiedStart(ModelView):
    'Open Annex Transactional Simplified Start'
    __name__ = 'account.open_annex_transactional_simplified.start'
    company = fields.Many2One('company.company', 'Company', required=True)
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)

    @staticmethod
    def default_fiscalyear():
        Fiscalyear = Pool().get('account.fiscalyear')
        return Fiscalyear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


class OpenAnnexTransactionalSimplified(Wizard):
    'Open Annex Transactional Simplified'
    __name__ = 'account.open_annex_transactional_simplified'
    
    start = StateView('account.open_annex_transactional_simplified.start',
        'account.open_annex_transactional_simplified_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('account.report_annex_transactional_simplified')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class AnnexTransactionalSimplified(Report):
    __name__ = 'account.annex_transactional_simplified'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Party = pool.get('party.party')
        MoveLine = pool.get('account.move.line')
        Move = pool.get('account.move')
        Account = pool.get('account.account')
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        Company = pool.get('company.company')
        Date = pool.get('ir.date')
        
        cursor = Transaction().cursor

        line = MoveLine.__table__()
        move = Move.__table__()
        account = Account.__table__()

        company = Company(data['company'])
        localcontext['company'] = company
        localcontext['digits'] = company.currency.digits
        localcontext['fiscalyear'] = data['fiscalyear']
        localcontext['totalVentas']=cls._get_ventas(Invoice, invoice)
        
     
