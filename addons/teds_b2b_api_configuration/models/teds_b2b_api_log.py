from openerp import models, fields, api
from datetime import timedelta,datetime
from openerp.exceptions import Warning

class B2bApiLog(models.Model):
    _name = "teds.b2b.api.log"
    _order = "date DESC"

    def _get_default_date(self):
        return datetime.now()

    name = fields.Char('Name')
    type = fields.Selection([
        ('incoming','Incoming'),
        ('outgoing','Outgoing')],string="Type")
    url = fields.Char('URL')
    request_type = fields.Selection([
        ('post','POST'),
        ('get','GET'),
        ('put','PUT'),
        ('delete','Delete')],string="Request Type")
    request = fields.Text('Request')
    response_code = fields.Char('Response Status')
    response = fields.Text('Response')
    date = fields.Datetime('Date',default=_get_default_date)
    jml_data = fields.Float('Jumlah Data')

    def create_log_api(self,name,type,url,request_type,request,response_code,response,jml_data=False):
        self.create({
            'name':name,
            'type':type,
            'url':url,
            'request_type':request_type,
            'request':request,
            'response_code':response_code,
            'response':response,
            'jml_data':jml_data
        })

    @api.multi
    def unlink(self):
        raise Warning("Log tidak boleh dihapus !")
        return super(B2bApiLog, self).unlink()