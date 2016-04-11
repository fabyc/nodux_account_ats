#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .party import *
from .account import *
from .invoice import *
def register():
    Pool.register(
        ATSStart,
        ATSExportResult,
        Party,
        Invoice,
        SustentoComprobante,
        module='nodux_account_ats', type_='model')
    Pool.register(
        ATSExport,
        module='nodux_account_ats', type_='wizard')
