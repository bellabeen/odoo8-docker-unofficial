from openerp import models, fields, api, _
from datetime import datetime, timedelta
import calendar

class wtc_purchase_order_type(models.Model):
	_name = "wtc.purchase.order.type"

	name = fields.Char()
	category = fields.Selection([
			('Unit','Unit'),
			('Sparepart','Sparepart'),
			('Umum','Umum'),
		], string='Type')
	date_start = fields.Selection([
			('now','Now'),
			('end_of_month','End of Month'),
			('next_month', 'Beginning of Next Month'),
			('end_of_next_month','End of Next Month'),
			('next_2_months','Beginning of Next two Months'),
			('end_of_next_2_months', 'End of Next two Months'),
		], string='Start Date')
	date_end = fields.Selection([
			('now','Now'),
			('end_of_month','End of Month'),
			('next_month', 'Beginning of Next Month'),
			('end_of_next_month','End of Next Month'),
			('next_2_months','Beginning of Next two Months'),
			('end_of_next_2_months', 'End of Next two Months'),
		], string='End Date')

	def get_date(self,date_type) :
		now = datetime.today()

		if date_type == 'now':
			return now
		elif date_type == 'end_of_month':
			return datetime(now.year, now.month, calendar.monthrange(now.year,now.month)[1])
		elif date_type == 'next_month':
			return datetime(now.year+1 if now.month+1>12 else now.year, now.month+1-12 if now.month+1>12 else now.month+1, 1)
		elif date_type == 'end_of_next_month':
			return datetime(now.year+1 if now.month+1>12 else now.year, now.month+1-12 if now.month+1>12 else now.month+1, calendar.monthrange(now.year,now.month+1)[1])
		elif date_type == 'next_2_months':
			return datetime(now.year+2 if now.month+2>12 else now.year, now.month+2-12 if now.month+2>12 else now.month+2, 1)
		elif date_type == 'end_of_next_2_months':
			return datetime(now.year+2 if now.month+2>12 else now.year, now.month+2-12 if now.month+2>12 else now.month+2, calendar.monthrange(now.year,now.month+2)[1])
		
		return now
		
