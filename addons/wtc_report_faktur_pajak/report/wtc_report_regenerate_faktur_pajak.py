from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_regenerate_faktur_pajak_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_regenerate_faktur_pajak_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        model_ids = data['model_ids']        
        state_regenerate_faktur_pajak = data['state_regenerate_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(self.cr, self.uid, 'Account')
              
        query = """
            select rfp.id as rfp_id,rfp.name as ref,
            m.name as form_name,
            rfp.date as date,
            rfp.state as state,
            pajak.total as total_line,
            l.name as transaction_no,
            l.untaxed_amount as untaxed_amount,
            l.tax_amount as tax_amount,
            l.amount_total as total_amount,
            p.default_code as partner_code,
            p.name as partner_name,
            l.date as date_order,
            fp.name as no_faktur
            from wtc_regenerate_faktur_pajak_gabungan rfp
            left join ir_model m on m.id = rfp.model_id
            left join wtc_regenerate_faktur_pajak_gabungan_line l on l.regenerate_id = rfp.id
            left join res_partner p on p.id = l.partner_id
            left join wtc_faktur_pajak_out fp on fp.id = l.no_faktur_pajak
            left join (select regenerate_id,count(id) as total from wtc_regenerate_faktur_pajak_gabungan_line group by regenerate_id) pajak on pajak.regenerate_id = rfp.id 
            where rfp.id is not null 
        """
        query_end = ''
        if model_ids :
            query_end += " AND m.id in %s" % str(
                tuple(model_ids)).replace(',)', ')')  
        if start_date :
            query_end += " AND rfp.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND rfp.date <= '%s' " % str(end_date)
        if state_regenerate_faktur_pajak :
            query_end += " AND rfp.state = '%s'" % str(state_regenerate_faktur_pajak) 
                                               
        query_order = "order by rfp.name,rfp.date"
        self.cr.execute(query + query_end + query_order)
        
        all_lines = self.cr.dictfetchall()
        pajak = []
        if all_lines and len(all_lines) < 65000:
            datas = map(lambda x : {
                'rfp_id': x['rfp_id'],
                'no': 0,
                'ref': str(x['ref']),
                'form_name': str(x['form_name']),
                'date': str(x['date']),
                'state': str(x['state']),
                'total_line': x['total_line'],
                'transaction_no': str(x['transaction_no']),
                'total_amount': x['total_amount'],
                'untaxed_amount': x['untaxed_amount'],
                'tax_amount': x['tax_amount'],
                'partner_code':str(x['partner_code']),
                'partner_name':str(x['partner_name']),
                'date':str(x['date_order']),
                'no_faktur':str(x['no_faktur']) if x['no_faktur'] else '',
                }, all_lines)
            for p in datas:
                if p['rfp_id'] not in map(lambda x: x.get('rfp_id', None), pajak):
                    pajak.append(p)
                    pajak_lines = filter(lambda x: x['rfp_id'] == p['rfp_id'], all_lines)
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
                                'rfp_id': 0,
                                'no': 0,
                                'ref': value,
                                'form_name': value,
                                'date': value,
                                'state': value,
                                'total_line': 0,
                                'transaction_no': value,
                                'total_amount': 0,
                                'untaxed_amount': 0,
                                'tax_amount': 0,
                                'partner_code':value,
                                'partner_name':value,
                                'date':value,
                                'no_faktur':value,
                                'sum_total_amount': 0,
                                'sum_untaxed_amount': 0,
                                'sum_tax_amount': 0,                                
                                'lines':[{
                                        'rfp_id': 0,
                                        'no': 0,
                                        'ref': value,
                                        'form_name': value,
                                        'date': value,
                                        'state': value,
                                        'total_line': 0,
                                        'transaction_no': value,
                                        'total_amount': 0,
                                        'untaxed_amount': 0,
                                        'tax_amount': 0,
                                        'partner_code':value,
                                        'partner_name':value,
                                        'date':value,
                                        'no_faktur':value,                                   
                                        }]
                    }]}]
        self.localcontext.update({'reports': reports})
        super(wtc_report_regenerate_faktur_pajak_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_regenerate_faktur_pajak_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_faktur_pajak.report_regenerate_faktur_pajak'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_faktur_pajak.report_regenerate_faktur_pajak'
    _wrapped_report_class = wtc_report_regenerate_faktur_pajak_print
    