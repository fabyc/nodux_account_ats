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

class Invoice():
    __name__ = 'account.invoice'

    numero_autorizacion_invoice = fields.Char(u'Número de autorización', size=49, states={
            'invisible': Eval('type') != 'in_invoice',
            'readonly' : Eval('state') != 'draft',
            })

    fecha_autorizacion = fields.Date(u'Fecha de autorizacion', states={
            'invisible': Eval('type') != 'in_invoice',
            'readonly' : Eval('state') != 'draft',
            })

    exclude_ats = fields.Boolean('Not include in ATS', states={
            'invisible': Eval('type') != 'in_invoice',
            'readonly': Eval('state') != 'draft',
            })

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()

    @staticmethod
    def default_exclude_ats():
        return False
