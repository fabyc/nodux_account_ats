#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .party import *
from .account import *
from .invoice import *
from .tax import *

def register():
    Pool.register(
        SustentoComprobante,
        ATSStart,
        ATSExportResult,
        Party,
        Invoice,
        PrintTalonStart,
        TaxElectronic,
        Tax,
        TaxSpecial,
        GenerateSummaryPurchasesStart,
        module='nodux_account_ats', type_='model')
    Pool.register(
        ReportTalon,
        ReportSummaryPurchases,
        module='nodux_account_ats', type_='report')
    Pool.register(
        ATSExport,
        PrintTalon,
        GenerateSummaryPurchases,
        module='nodux_account_ats', type_='wizard')
