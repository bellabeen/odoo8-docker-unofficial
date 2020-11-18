from openerp.osv import osv

class web_service_hoo(osv.osv):
	_inherit = "stock.quant"

	def get_stock_available(self,cr,uid,ids, product_name, branch_code):
		query = """
				select product_id, sum(qty) as jum_qty 
				from stock_quant
				where product_id = (select id from product_product where name_template='%s') and
					location_id in (select l.id from stock_location l left join wtc_branch b on l.branch_id = b.id where l.usage='internal' and b.code = '%s') and
					reservation_id IS NULL
				group by product_id
				""" % (product_name, branch_code)
		cr.execute (query)
		ress = cr.fetchall()
		jum = 0
		if (len(ress)>0):
			jum=ress[0][1]
		else:
			jum=0

		return jum