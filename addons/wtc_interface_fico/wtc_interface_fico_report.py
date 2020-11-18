class wtc_interface_fico_report(osv.osv_memory):
	_name = 'wtc.report.interface.fico'
	_description = 'Report Interface FICO'

	_columns = {
		'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
		'data_x': fields.binary('File', readonly=True),
		'name': fields.char('Filename', 100, readonly=True),
		'option': fields.selection([('jm', 'Journal Entries'),('all','Transaction on Date')], 'Option', change_default=True, select=True, required=True),
		'date': fields.date('Date'),
		'account_move_ids': fields.many2many('account.move', 'wtc_report_interface_fico_account_move_rel', 'wtc_report_interface_fico_id',
                                        'account_move_id', 'Journal Entries', copy=False),
	}

    _defaults = {
        'state_x': lambda *a: 'choose',
        'date':datetime.today(),
        'option':'jm'
    }

    def generate_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]

        date = False
        move_ids = []

        filename = ''
        if data.option == 'jm' :
        	move_ids = date.account_move_ids
	        filename = 'JIT-JM.txt'
        elif data.option == 'all' :
        	date = data.date
        	filename = 'JIT-'+date.strftime("%Y%m%d")+'.txt'

        jit = self.pool.get('wtc.interface.fico').export_jit(date, move_ids)
        out=base64.encodestring(jit)

        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_interface_fico', 'view_report_interface_fico')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.interface.fico',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

