# -*- coding: utf-8 -*-

from trytond.pyson import Eval
from trytond.model import ModelSQL, Workflow, fields, ModelView
from trytond.report import Report
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

import time
__all__ = ['Invoice']
__metaclass__ = PoolMeta

_FORMAS = [
('', ''),
('01', u'SIN UTILIZACIÓN DEL SISTEMA FINANCIERO'),
('02', u'CHEQUE PROPIO'),
('03', u'CHEQUE CERTIFICADO'),
('04', u'CHEQUE DE GERENCIA'),
('05', u'CHEQUE DEL EXTERIOR'),
('06', u'DÉBITO DE CUENTA'),
('07', u'TRANSFERENCIA PROPIO BANCO'),
('08', u'TRANSFERENCIA OTRO BANCO NACIONAL'),
('08', u'TRANSFERENCIA  BANCO EXTERIOR'),
('10', u'TARJETA DE CRÉDITO NACIONAL'),
('11', u'TARJETA DE CRÉDITO INTERNACIONAL'),
('12', u'GIRO'),
('13', u'DEPÓSITO EN CUENTA (CORRIENTE/AHORROS)'),
('14', u'ENDOSO DE INVERSIÓN'),
('15', u'COMPENSACIÓN DE DEUDAS'),
]

class Invoice():

    __name__ = 'account.invoice'
    
    formas_de_pago = fields.Selection(_FORMAS, 'Formas de Pago', states={
            'invisible': Eval('type') != 'in_invoice',
            }, help = u'Seleccionar una forma de pago, cuando monto a pagar sea mayor a $1000')
      
    numero_autorizacion = fields.Char(u'Número de autorización', size=49, states={
            'invisible': Eval('type') != 'in_invoice',
            })
            
    impuestos_ats_renta = fields.Many2One('account.tax', 'Impuesto Renta ATS')
    
    impuesto_ats_iva = fields.Many2One('account.tax', 'Impuesto IVA ATS')
            
    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()

