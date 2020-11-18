import time
from openerp.osv import osv
from openerp.report import report_sxw

class print_location(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(print_location, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'get_total_amount': self._get_total_amount,
            'get_untaxed_amount': self._get_untaxed_amount,
            'get_tax_amount': self._get_tax_amount,
            'get_default': self._get_default,
            'tgl': self.get_date,
        })

        self.no = 0

    def no_urut(self):
        self.no+=1
        return self.no



 
        
    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)

   
     
    def get_date(self):
        date= self._get_default_date(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d")
        return date

    def _get_default_date(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
       

class print_location_location(osv.AbstractModel):
    _name = 'report.teds_sub_location.report_location'
    _inherit = 'report.abstract_report'
    _template = 'teds_sub_location.report_location'
    _wrapped_report_class = print_location

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
