{
	'name': 'TEDS TOP UP',
	'version': '1.0',
	'description': 'TEDS Top Up',
	'summary': 'TEDS Top Up',
	'sequence': '1', 
  	'category': 'TDM',
	'author': 'Febrasari Almania',
	'email': 'febrasari.almania@gmail.com',
	'depends': [
		'base',
		'product',
		'wtc_branch',
		'wtc_p2p',
		'wtc_purchase_order',
		'wtc_dealer_menu',
		'wtc_stock'
	],
	'demo': [],
	'data': [
		'data/wtc_purchase_order_type_data.xml',
		'views/teds_stock_ideal_view.xml',
		'views/teds_topup_view.xml',
		'security/res_groups.xml',
        'security/ir.model.access.csv',
	],
	'active': False,
	'installable': True
}
