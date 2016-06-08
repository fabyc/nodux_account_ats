#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pyson import Id
from trytond.pool import Pool, PoolMeta
from trytond import backend
from trytond.transaction import Transaction

__all__ = ['Party']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'required': True,
}
DEPENDS = ['active']


class Party:
    __name__ = 'party.party'

    tipo_sustento = fields.Many2One('account.sustento', 'Sustento Tributario')

    parte_relacional = fields.Selection([
            ('',''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Parte Relacional')

    tipo_de_pago = fields.Selection([
            ('', ''),
            ('01', 'Residente'),
            ('02', 'No residente'),
            ], 'Pago realizado a')

    #indicar si el pago realizado aun no residente se encuentra en un regimen fiscal preferente o de menor imposicion.
    pago_regimen = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Pago  es a un regimen fiscal', help ='Pago  es a un regimen fiscal preferente o de menor imposicion',states={
            'invisible': Eval('tipo_de_pago')!= '02',
            })

    #cuando el codigo del campo pago local o al exterior sea igual a 02 (no residente)
    convenio_doble = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Aplica convenio de doble tributacion', help ='Aplica convenio de doble tributacion',states={
            'invisible': Eval('tipo_de_pago')!= '02',
            })

    #cuando Aplica convenio de doble tributacion = no
    sujeto_retencion = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ],'Sujeto a retencion', help='Pago al exterior sujeto a retencion en aplicacion a la norma legal', states={
            'invisible': Eval('convenio_doble')!= 'NO',
            })
            
    tipo_proveedor = fields.Selection([
            ('', ''),
            ('01', 'Persona Natural'),
            ('02', 'Sociedad'),
            ], u'Identificacion del Proveedor', help ='Tipo de identificacion del Proveedor', states={
            'invisible': Eval('type_document')!= '07',
            })

    @staticmethod
    def default_parte_relacional():
        return 'NO'

    @staticmethod
    def default_tipo_de_pago():
        return '01'

    @staticmethod
    def default_convenio_doble():
        return 'NO'

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()

