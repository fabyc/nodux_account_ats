#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pyson import Id

__all__ = ['Party']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'required': True,
}
DEPENDS = ['active']

#Agrega tipo de sustento a tercero
_SUSTENTO=[
('01',u'Crédito Tributario para declaración de IVA (servicios y bienes distintos de inventarios y activos fijos)'),
('02',u'Costo o Gasto para declaración de IR (servicios y bienes distintos de inventarios y activos fijos)'),
('03',u'Activo Fijo - Crédito Tributario para declaración de IVA'),
('04',u'Activo Fijo - Costo o Gasto para declaración de IR'),
('05',u'Liquidación Gastos de Viaje, hospedaje y alimentación Gastos IR (a nombre de empleados y no de la empresa)'),
('06',u'Inventario - Crédito Tributario para declaración de IVA'),
('07',u'Inventario - Costo o Gasto para declaración de IR'),
('08',u'Valor pagado para solicitar Reembolso de Gasto (intermediario)'),
('09',u'Reembolso por Siniestros'),
('10',u'Distribución de Dividendos, Beneficios o Utilidades'),
('11',u'Convenios de débito o recaudación para IFIs'),
('12',u'Impuestos y retenciones presuntivos'),
('13',u'Valores reconocidos por entidades del sector público a favor de sujetos pasivos'),
('00','Casos especiales cuyo sustento no aplica en las opciones anteriores'),
] 

class Party:
    __name__ = 'party.party'
    
    type_sustent = fields.Selection(_SUSTENTO, 'Tipo de Sustento', select= True,
        required=True)
        
    parte_relacional = fields.Selection([
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Parte Relacional', required=True)
            
    tipo_de_pago = fields.Selection([
            ('01', 'Residente'),
            ('02', 'No residente'),
            ],u'Pago realizado a', required=True)
 
    convenio_doble = fields.Selection([
            ('SI', 'Si'),
            ('NO', 'No'),
            ], u'Convenio de doble Tributación', states={
            'invisible': Eval('tipo_de_pago') != '01',
            'required': Eval('tipo_de_pago') == '02',
            })
    
    sujeto_retencion = fields.Selection([
            ('SI', 'Si'),
            ('NO', 'No'),
            ], u'Pago al exterior sujeto a retención en aplicación a la norma legal', states={
            'invisible': Eval('convenio_doble')!= 'NO',
            'required': Eval('convenio_doble') == 'SI',
            })        
    
    pago_regimen = fields.Selection([
            ('SI', 'Si'),
            ('NO', 'No'),
            ]u'Pago  es a un régimen fiscal preferente o de menor imposición', states={
            'invisible': Eval('tipo_de_pago')!= '02',
            'required': Eval('tipo_de_pago')=='02'
            })
    
    
    
    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
       
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
    def search_rec_name(cls, name, clause):
        parties = cls.search([
                ('vat_number',) + tuple(clause[1:]),
                ], limit=1)
        if parties:
            return [('vat_number',) + tuple(clause[1:])]
        return [('name',) + tuple(clause[1:])]

    def reeplace_code ()
