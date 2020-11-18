import time
from openerp.osv import orm, fields
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class report_dealer_sale_order_wizard(orm.TransientModel):
    _name = 'report.dealer.sale.order.wizard'
    _description = 'Report Dealer Sale order Wizard'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_dealer_sale_order_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'date_from': fields.date("Start Date"),
        'date_to': fields.date("End Date"),
        'branch_ids': fields.many2many('wtc.branch', 'report_sale_order_invoice_rel', 'report_sale_order_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'state': fields.selection([
                                ('draft', 'Draft Quotation'),
                                ('waiting_for_approval','Waiting Approval'),
                                ('approved','Approved'),                                
                                ('progress', 'Sales Order'),
                                ('done', 'Done'),
                                ],'Status',),
        'jenis_penjualan': fields.selection([
                                ('cash', 'Cash'),
                                ('kredit','Kredit'),
                                ],'Jenis Pembelian',),
        }
   
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        cek=len(branch_ids)
        
        if cek == 0 :
            branch_ids=[b.id for b in branch_ids_user]
        else :
            branch_ids=data['branch_ids']


        date_from = data['date_from']
        date_to = data['date_to']
        state = data['state']
        jenis_penjualan = data['jenis_penjualan']

        data.update({
            'branch_ids': branch_ids,
            'date_from': date_from,
            'date_to': date_to,
            'state': state,
            'jenis_penjualan': jenis_penjualan,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dealer.sale.order.report.xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dealer_sale_order.report_dealer_sale_order',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
