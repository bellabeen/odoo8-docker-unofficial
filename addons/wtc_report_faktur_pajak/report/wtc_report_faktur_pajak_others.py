from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_faktur_pajak_others_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_faktur_pajak_others_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        pajak_gabungan = data['pajak_gabungan']
        partner_ids = data['partner_ids']
        state_other_faktur_pajak = data['state_other_faktur_pajak']
        thn_penggunaan = data['thn_penggunaan']
        start_date = data['start_date']
        end_date = data['end_date']
        
        query = """
        select fpo.name as reference, fp.name as no_faktur,
        p.default_code as partner_code, p.name as partner_name,
        fpo.date as date,
        fpo.pajak_gabungan as pajak_gabungan,
        fpo.thn_penggunaan as thn_penggunaan,
        fpo.tgl_terbit as tgl_terbit,
        fpo.kwitansi_no as no_kwitansi,
        fpo.untaxed_amount as untaxed_amount,
        fpo.total_amount as amount_total,
        fpo.tax_amount as tax_amount,
        fpo.state as state
        from wtc_faktur_pajak_other fpo
        inner join wtc_faktur_pajak_out fp ON fp.id = fpo.faktur_pajak_id
        inner join res_partner p ON p.id = fpo.partner_id
        where fpo.id is not null 
        """
        query_end = ''
        if start_date :
            query_end += " AND fpo.date >= '%s'" % str(start_date)
            
        if end_date :
            query_end += " AND fpo.date <= '%s'" % str(end_date)
                            
        if pajak_gabungan :
            query_end += " AND fpo.pajak_gabungan = 't' "
            
        if state_other_faktur_pajak :
            query_end += " AND fpo.state = '%s'" % str(state_other_faktur_pajak)
            
        if thn_penggunaan :
            query_end += " AND fpo.thn_penggunaan = '%s'" % str(thn_penggunaan)  
                
        if partner_ids :
            query_end += " AND p.id in %s" % str(tuple(partner_ids)).replace(',)', ')')
                        
        query_order = "order by fpo.name, fpo.id"
        
        self.cr.execute(query + query_end + query_order)
        all_lines = self.cr.dictfetchall()
        
        if all_lines and len(all_lines) < 65000:
            datas = map(lambda x : {
                'no': 0,
                'reference': str(x['reference'].encode('ascii','ignore').decode('ascii')) if x['reference'] != None else '',
                'no_faktur': str(x['no_faktur'].encode('ascii','ignore').decode('ascii')) if x['no_faktur'] != None else '',
                'partner_code': str(x['partner_code']),
                'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                'date': str(x['date'].encode('ascii','ignore').decode('ascii')) if x['date'] != None else '',
                'pajak_gabungan':  str(x['pajak_gabungan']),
                'thn_penggunaan': str(x['thn_penggunaan']),
                'tgl_terbit': str(x['tgl_terbit']),
                'no_kwitansi': str(x['no_kwitansi']),
                'untaxed_amount': x['untaxed_amount'],
                'tax_amount': x['tax_amount'],
                'amount_total':x['amount_total'],
                'state': str(x['state']),
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            value = False
            if len(all_lines) > 65000 :
                value = 'OVER LOAD'
            else :
                value = 'NO DATA FOUND'
            reports = [{'datas': [{
                'no': 0,
                'reference': value,
                'no_faktur': value,
                'partner_code':value,
                'partner_name': value,
                'date': value,
                'pajak_gabungan':  value,
                'thn_penggunaan': value,
                'tgl_terbit': value,
                'no_kwitansi':value,
                'untaxed_amount':0,
                'tax_amount': 0,
                'amount_total':0,
                'state':value,
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(wtc_report_faktur_pajak_others_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_faktur_pajak_others_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_faktur_pajak_others.report_faktur_pajak_others'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_faktur_pajak_others.report_faktur_pajak_others'
    _wrapped_report_class = wtc_report_faktur_pajak_others_print
    