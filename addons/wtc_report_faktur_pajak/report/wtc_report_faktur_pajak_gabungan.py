from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_faktur_pajak_gabungan_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_faktur_pajak_gabungan_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        branch_ids = data['branch_ids']
        division = data['division']
        partner_ids = data['partner_ids']        
        state_gabungan_faktur_pajak = data['state_gabungan_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(self.cr, self.uid, 'Account')
              
        query = """
            SELECT fpg.id as fpg_id, b.code as branch_code, fpg.division as division, 
            fpg.name as transaction_ref, fp.name as code_pajak, fpg.date as date, 
            fpg.start_date as start_date, fpg.end_date as end_date,
            p.default_code as partner_code, p.name as partner_name, 
            fpg.date_pajak as tgl_document, pajak.total as count_line,m.name as model_name,
            l.name as transaction_no, l.date as transaction_date, 
            l.untaxed_amount as untaxed_amount, 
            l.tax_amount as tax_amount,
            l.total_amount as total_amount,
            fpg.state as state
            FROM wtc_faktur_pajak_gabungan fpg
            left join wtc_branch b on b.id = fpg.branch_id
            left join wtc_faktur_pajak_out fp on fp.id = fpg.faktur_pajak_id
            left join res_partner p ON p.id = fpg.customer_id
            left join wtc_faktur_pajak_gabungan_line l ON l.pajak_gabungan_id = fpg.id
            left join ir_model m ON m.model = l.model
            left join (select pajak_gabungan_id,count(id) as total from wtc_faktur_pajak_gabungan_line group by pajak_gabungan_id) pajak on pajak.pajak_gabungan_id = fpg.id    
            where fpg.name is not null        
        """
        query_end = ''
        if branch_ids :
            query_end += " AND fpg.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_end += " AND fpg.customer_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')  
        if start_date :
            query_end += " AND fpg.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND fpg.date <= '%s' " % str(end_date)
        if division :
            query_end += " AND fpg.division = '%s'" % str(division) 
        if state_gabungan_faktur_pajak :
            query_end += " AND fpg.state = '%s'" % str(state_gabungan_faktur_pajak) 
                                               
        query_order = "order by b.code,fpg.date"
        self.cr.execute(query + query_end + query_order)
        
        all_lines = self.cr.dictfetchall()
        pajak = []
        if all_lines and len(all_lines) < 65000:
            datas = map(lambda x : {
                'fpg_id': x['fpg_id'],
                'no': 0,
                'transaction_ref': str(x['transaction_ref'].encode('ascii','ignore').decode('ascii')) if x['transaction_ref'] != None else '',
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                'code_pajak': str(x['code_pajak']),
                'date': str(x['date'].encode('ascii','ignore').decode('ascii')) if x['date'] != None else '',
                'start_date': str(x['start_date']),
                'end_date':  str(x['end_date']),
                'partner_code': str(x['partner_code']),
                'partner_name': str(x['partner_name']),
                'tgl_document': str(x['tgl_document']),
                'count_line' : x['count_line'],
                'transaction_no': str(x['transaction_no'].encode('ascii','ignore').decode('ascii')) if x['transaction_no'] != None else '',
                'transaction_date': str(x['transaction_date'].encode('ascii','ignore').decode('ascii')) if x['transaction_date'] != None else '',
                'model_name': str(x['model_name']),
                'total_amount': x['total_amount'],
                'untaxed_amount': x['untaxed_amount'],
                'tax_amount': x['tax_amount'],
                'state':str(x['state'])
                }, all_lines)
            for p in datas:
                if p['fpg_id'] not in map(lambda x: x.get('fpg_id', None), pajak):
                    pajak.append(p)
                    pajak_lines = filter(lambda x: x['fpg_id'] == p['fpg_id'], all_lines)
                    p.update({'lines': pajak_lines})   
                      
                    total_amount = map(lambda x: x['total_amount'] or 0.0, pajak_lines)
                    sum_total_amount = reduce(lambda x, y: x + y, total_amount)
                    sum_total_amount = round(sum_total_amount, digits)
                    
                    untaxed_amount = map(lambda x: x['untaxed_amount'] or 0.0, pajak_lines)
                    sum_untaxed_amount = reduce(lambda x, y: x + y, untaxed_amount)
                    sum_untaxed_amount = round(sum_untaxed_amount, digits)

                    tax_amount = map(lambda x: x['tax_amount'] or 0.0, pajak_lines)
                    sum_tax_amount = reduce(lambda x, y: x + y, tax_amount)
                    sum_tax_amount = round(sum_tax_amount, digits)
                                          
                    p.update(
                        {'sum_total_amount': sum_total_amount,
                         'sum_untaxed_amount': sum_untaxed_amount,
                         'sum_tax_amount': sum_tax_amount})
                                            
            reports = filter(lambda x: pajak, [{'pajak': pajak}])
        else :
            value = False
            if len(all_lines) > 65000 :
                value = 'OVER LOAD'
            else :
                value = 'NO DATA FOUND'
            reports = [{'pajak': [{
                                'fpg_id': 0,
                                'no': 0,
                                'transaction_ref': value,
                                'branch_code': value,
                                'division': value,
                                'code_pajak': value,
                                'date': value,
                                'start_date': value,
                                'end_date':  value,
                                'partner_code': value,
                                'partner_name': value,
                                'tgl_document': value,
                                'count_line' : 0,
                                'transaction_no':value,
                                'transaction_date': value,
                                'model_name': value,
                                'total_amount': 0,
                                'untaxed_amount':0,
                                'tax_amount': 0,
                                'sum_total_amount':0,
                                'sum_untaxed_amount':0,
                                'sum_tax_amount':0,
                                'state':value,
                                'lines':[{
                                        'fpg_id': 0,
                                        'no': 0,
                                        'transaction_ref': value,
                                        'branch_code': value,
                                        'division': value,
                                        'code_pajak': value,
                                        'date': value,
                                        'start_date': value,
                                        'end_date':  value,
                                        'partner_code': value,
                                        'partner_name': value,
                                        'tgl_document': value,
                                        'count_line' : 0,
                                        'transaction_no':value,
                                        'transaction_date': value,
                                        'model_name': value,
                                        'total_amount': 0,
                                        'untaxed_amount':0,
                                        'tax_amount': 0,
                                        'sum_total_amount':0,
                                        'sum_untaxed_amount':0,
                                        'sum_tax_amount':0,  
                                        'state':value,                                      
                                        }]
                    }]}]
        self.localcontext.update({'reports': reports})
        super(wtc_report_faktur_pajak_gabungan_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_faktur_pajak_gabungan_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_faktur_pajak.report_faktur_pajak_gabungan'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_faktur_pajak.report_faktur_pajak_gabungan'
    _wrapped_report_class = wtc_report_faktur_pajak_gabungan_print
    