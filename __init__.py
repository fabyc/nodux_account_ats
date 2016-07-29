#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .party import *
from .account import *
from .invoice import *

def register():
    Pool.register(
        SustentoComprobante,
        ATSStart,
        ATSExportResult,
        Party,
        Invoice,
        PrintTalonStart,
        module='nodux_account_ats', type_='model')
    Pool.register(
        ReportTalon,
        module='nodux_account_ats', type_='report')
    Pool.register(
        ATSExport,
        PrintTalon,
        module='nodux_account_ats', type_='wizard')
