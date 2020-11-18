from openerp.osv import fields, osv
from datetime import datetime
import xlsxwriter

class wtc_report_stock_distribution(osv.osv_memory):
    _name = "wtc.report.stock.distribution"
    _description = "Report Stock Distribution"

    wbf = {}

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))),
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'options': fields.selection([('sd_detail','Stock Distribution Detail'),('sd_order',"Stock Distribution's Mutation Order")], 'Options', change_default=True, select=True),
        'state': fields.selection([('requested','Requested'),('open','Open'),('done','Done'),('open_done','Open & Done'),('open_done_cancel','Open, Done & Cancelled'),('reject','Rejected'),('all','All')], "Stock Distribution's State", change_default=True, select=True),
        'order_state': fields.selection([('all','All'),('draft','Draft'),('confirm','In Progress'),('done','Done'),('cancel','Cancelled')], "Order's State", change_default=True, select=True),
        'trx_type': fields.selection([('all','All'),('mutation','Mutation'),('sales','Sales')], 'Transaction Type'),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_distribution_branch_rel', 'wtc_report_stock_distribution', 'branch_id', 'Branches', copy=False),
        'dealer_ids': fields.many2many('res.partner', 'wtc_report_stock_distribution_partner_rel', 'wtc_report_stock_distribution', 'partner_id', 'Partners', copy=False),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options':'sd_detail'
    }

    def add_workbook_format(self, cr, uid, workbook):
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')

        self.wbf['footer'] = workbook.add_format({'align':'left'})

        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()

        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right()

        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)

        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)

        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()

        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right()
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})

        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right()
        self.wbf['content_number'].set_left()

        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right()
        self.wbf['content_percent'].set_left()

        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()

        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()

        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()

        return workbook

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res = False
        data = self.read(cr, uid, ids,context=context)[0]

        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        if data['options'] == 'sd_detail' :
            res = self._print_excel_report_detail(cr, uid, ids, data, context=context)
        else :
            res = self._print_excel_report_order(cr, uid, ids, data, context=context)

        if res :
            ir_model_data = self.pool.get('ir.model.data')
            form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock_distribution', 'view_report_stock_distribution')

            form_id = form_res and form_res[1] or False
            return {
                'name': 'Download XLS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wtc.report.stock.distribution',
                'res_id': ids[0],
                'view_id': False,
                'views': [(form_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'current'
            }
        else :
            raise except_orm('Perhatian!', 'Silahkan ulangi lagi.')
