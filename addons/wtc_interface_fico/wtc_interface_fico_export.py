from openerp.osv import fields, osv
from datetime import datetime
import pytz
from pytz import timezone
import base64

class wtc_interface_fico_export(osv.osv_memory):
    _name = 'wtc.interface.fico.export'
    _description = 'Export Interface FICO'

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))),
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'options': fields.selection([('jm', 'Journal Entries'),('all','Transaction on Date')], 'Option', change_default=True, select=True, required=True),
        'period_id': fields.many2one('account.period', string='Period'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'account_move_ids': fields.many2many('account.move', 'wtc_interface_fico_export_account_move_rel', 'wtc_interface_fico_export_id',
            'account_move_id', 'Journal Entries', copy=False),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'option': lambda *a: 'all',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
    }

    def generate_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        data = self.browse(cr, uid, ids,context=context)[0]

        date = pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))
        move_ids = []

        filename = 'JIT-EXP-'+date.strftime("%Y%m%d")+'.txt'
        if data.options == 'jm' :
            move_ids = [move.id for move in data.account_move_ids]
        elif data.options == 'all' :
            cr.execute("select id from account_move where period_id = %s and create_date + interval '7 hours' BETWEEN '%s 00:00:00' AND '%s 23:59:59'" % (data.period_id.id, data.start_date, data.end_date))
            data = cr.fetchall()
            move_ids = [datum[0] for datum in data]

        if len(move_ids) == 0 :
            raise osv.except_osv('Perhatian !', "Tidak ada data yang sesuai kriteria!")

        jit = self.pool.get('wtc.interface.fico').export_jit(cr, uid, None, move_ids)
        out=base64.encodestring(jit)

        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_interface_fico', 'view_export_fico_wizard_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': 'Download File',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.interface.fico.export',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

