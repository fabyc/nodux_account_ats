#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pyson import Id
from trytond.pool import Pool, PoolMeta

__all__ = ['Party']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'required': True,
}
DEPENDS = ['active']

#Agrega tipo de sustento a tercero
_SUSTENTO=[
('01',u'Credito Tributario para declaracion de IVA (servicios y bienes distintos de inventarios y activos fijos)'),
('02',u'Costo o Gasto para declaracion de IR (servicios y bienes distintos de inventarios y activos fijos)'),
('03',u'Activo Fijo - Credito Tributario para declaracion de IVA'),
('04',u'Activo Fijo - Costo o Gasto para declaracion de IR'),
('05',u'Liquidacion Gastos de Viaje, hospedaje y alimentacion Gastos IR (a nombre de empleados y no de la empresa)'),
('06',u'Inventario - Credito Tributario para declaracion de IVA'),
('07',u'Inventario - Costo o Gasto para declaracion de IR'),
('08',u'Valor pagado para solicitar Reembolso de Gasto (intermediario)'),
('09',u'Reembolso por Siniestros'),
('10',u'Distribucion de Dividendos, Beneficios o Utilidades'),
('11',u'Convenios de debito o recaudacion para IFIs'),
('12',u'Impuestos y retenciones presuntivos'),
('13',u'Valores reconocidos por entidades del sector publico a favor de sujetos pasivos'),
('00','Casos especiales cuyo sustento no aplica en las opciones anteriores'),
] 
class Party:
    __name__ = 'party.party'
    
    type_sustent = fields.Selection(_SUSTENTO, 'Tipo de Sustento', select= True)
        
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
 
    convenio_doble = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Convenio de doble Tributacion', states={
            'invisible': Eval('tipo_de_pago') != '01',
            })
    
    sujeto_retencion = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ],'Sujeto a retencion', help='Pago al exterior sujeto a retencion en aplicacion a la norma legal', states={
            'invisible': Eval('convenio_doble')!= 'NO',
            })        
    
    pago_regimen = fields.Selection([
            ('', ''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Pago  es a un regimen fiscal', help ='Pago es a un regimen fiscal preferente o de menor imposicion',states={
            'invisible': Eval('tipo_de_pago')!= '02',
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

