from openerp.osv import fields, osv

class account_account(osv.osv):
    _inherit = 'account.account'
    _columns = {
		'sap': fields.char('SAP Code', size=64),
    }

class account_template(osv.osv):
	_inherit = 'account.account.template'
	_columns = {
		'sap': fields.char('SAP Code', size=64)
	}
