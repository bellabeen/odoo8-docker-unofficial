import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler

class wtc_purchase_requisition_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_purchase_requisition_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'get_total': self.get_total,
        })
        self.no = 0
    
    def no_urut(self):
        self.no+=1
        return self.no

      
    def get_total(self, o):
        total = 0
        for o in o.line_ids:
                total+= (o.product_qty)
        return total
         
    
     
report_sxw.report_sxw('report.rml.pr', 'purchase.requisition', 'addons/wtc_purchase_requisition/report/wtc_purchase_requisition_report.rml', parser = wtc_purchase_requisition_report, header = False)        
