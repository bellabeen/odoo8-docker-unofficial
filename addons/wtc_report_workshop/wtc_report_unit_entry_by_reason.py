import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
import time
import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree
from dateutil.rrule import *

class wtc_report_workshop(osv.osv_memory):
    _inherit = "wtc.report.workshop.wizard"
    wbf = {}






        # return True
wtc_report_workshop()