import time
from openerp.osv import orm, fields,osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from datetime import datetime


class wtc_report_control_control(orm.TransientModel):
    _name = 'wtc.report.control.df'
    _description = 'WTC Report Control DF'
    
    
    _columns = {
        'per_date': fields.date('Per Date',required=True),       
    }
    _defaults = {
        'per_date':datetime.today(),
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        per_date = data['per_date']

        data.update({
            'per_date': per_date,
            
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'wtc.report.control.df.xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'wtc_report_control_df_xls.report_control_df',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
