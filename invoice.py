# -*- coding: utf-8 -*-

from trytond.pyson import Eval
from trytond.model import ModelSQL, Workflow, fields, ModelView
from trytond.report import Report
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from decimal import Decimal

import time
__all__ = ['Invoice']
__metaclass__ = PoolMeta

_FORMAS = [
('', ''),
('01', u'01-SIN UTILIZACIÓN DEL SISTEMA FINANCIERO'),
('02', u'02-CHEQUE PROPIO'),
('03', u'03-CHEQUE CERTIFICADO'),
('04', u'04-CHEQUE DE GERENCIA'),
('05', u'05-CHEQUE DEL EXTERIOR'),
('06', u'06-DÉBITO DE CUENTA'),
('07', u'07-TRANSFERENCIA PROPIO BANCO'),
('08', u'08-TRANSFERENCIA OTRO BANCO NACIONAL'),
('08', u'09-TRANSFERENCIA  BANCO EXTERIOR'),
('10', u'10-TARJETA DE CRÉDITO NACIONAL'),
('11', u'11-TARJETA DE CRÉDITO INTERNACIONAL'),
('12', u'12-GIRO'),
('13', u'13-DEPÓSITO EN CUENTA (CORRIENTE/AHORROS)'),
('14', u'14-ENDOSO DE INVERSIÓN'),
('15', u'15-COMPENSACIÓN DE DEUDAS'),
]

class Invoice():

    __name__ = 'account.invoice'
    
    formas_de_pago = fields.Selection(_FORMAS, 'Formas de Pago', states={
            'invisible': Eval('type') != 'in_invoice',
            }, help = u'Seleccionar una forma de pago, cuando monto a pagar sea mayor a $1000')
      
    numero_autorizacion = fields.Char(u'Número de autorización', size=49, states={
            'invisible': Eval('type') != 'in_invoice',
            'required': Eval('type') == 'in_invoice',
            })
            
    fecha_autorizacion = fields.Date(u'Fecha de autorizacion', states={
            'invisible': Eval('type') != 'in_invoice',
            'required': Eval('type') == 'in_invoice',
            })    
    numero_factura = fields.Char(u'Numero de factura', states={
            'invisible': Eval('type') != 'in_invoice',
            'required': Eval('type') == 'in_invoice',
            })   
                 
    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()

