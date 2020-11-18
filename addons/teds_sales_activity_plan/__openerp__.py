{
	'name': 'Sales Activity Plan',
	'version': '1.0',
	'description': 'Sales Activity Plan',
	'summary': 'Sales Activity Plan',
	'sequence': '1', 
  	'category': 'TDM',
	'author': 'Febrasari Almania',
	'email': 'febrasari.almania@gmail.com',
	'depends': [
		'base',
		'wtc_branch',
		'wtc_dealer_menu'
	],
	'demo': [],
	"depends":["base","wtc_branch","wtc_dealer_menu"],
	'data': [
		'views/sales_activity_plan_view.xml',
		'views/master_activity_type_view.xml',
		#'data/master_activity_type_data.xml',
		#'security/ir.model.access.csv',
		'security/res_groups.xml',
		#'demo/master.ring.csv',
		#'demo/ring.kecamatan.csv',
		#'demo/ring.kecamatan.line.csv',
		#'demo/titik.keramaian.csv',
		#'demo/sales.plan.csv',
		#'demo/sales.plan.line.csv'
	],
	'active': False,
	'installable': True
}
