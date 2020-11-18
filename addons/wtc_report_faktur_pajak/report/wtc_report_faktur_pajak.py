from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_faktur_pajak_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_faktur_pajak_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        model_ids = data['model_ids']
        pajak_gabungan = data['pajak_gabungan']
        partner_ids = data['partner_ids']
        state_faktur_pajak = data['state_faktur_pajak']
        thn_penggunaan = data['thn_penggunaan']
        start_date = data['start_date']
        end_date = data['end_date']
                
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " fpo.tgl_terbit >= '%s'" % str(start_date)
            
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " fpo.tgl_terbit <= '%s'" % str(end_date)
                            
        where_pajak_gabungan = " 1=1 "
        if pajak_gabungan :
            where_pajak_gabungan = " fpo.pajak_gabungan = 't' "
            
        where_state_faktur_pajak = " 1=1 "
        if state_faktur_pajak :
            where_state_faktur_pajak = " fpo.state = '%s'" % str(state_faktur_pajak)
            
        where_thn_penggunaan = " 1=1 "
        if thn_penggunaan :
            where_thn_penggunaan = " fpo.thn_penggunaan = '%s'" % str(thn_penggunaan)  
                      
        where_model_ids = " 1=1 "
        if model_ids :
            where_model_ids = " m.id in %s" % str(
                tuple(model_ids)).replace(',)', ')')
                
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " p.id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        
        query_faktur_pajak = """
        select fpo.name as code_pajak,m.name as form_name,
        fpo.pajak_gabungan as pajak_gabungan,p.default_code as partner_code,
        p.name as partner_name, fpo.date as date, fpo.untaxed_amount as untaxed_amount,
        fpo.tax_amount as tax_amount,fpo.amount_total as amount_total,
        fpo.tgl_terbit as tgl_terbit, fpo.thn_penggunaan as thn_penggunaan,
        fpo.cetak_ke as cetak_ke, fpo.state as state
        from wtc_faktur_pajak_out fpo 
        left join ir_model m ON m.id = fpo.model_id
        left join res_partner p ON p.id = fpo.partner_id
        """
        
        where = "WHERE " + where_start_date +" AND "+ where_end_date +" AND "+ where_pajak_gabungan + " AND " + where_state_faktur_pajak + " AND " + where_thn_penggunaan + " AND " + where_model_ids + " AND " + where_partner_ids
        order = "order by fpo.name, fpo.id"
        
        self.cr.execute(query_faktur_pajak + where + order)
        all_lines = self.cr.dictfetchall()
        
        if all_lines and len(all_lines) < 65000:
            datas = map(lambda x : {
                'no': 0,
                'code_pajak': str(x['code_pajak'].encode('ascii','ignore').decode('ascii')) if x['code_pajak'] != None else '',
                'form_name': str(x['form_name'].encode('ascii','ignore').decode('ascii')) if x['form_name'] != None else '',
                'pajak_gabungan': str(x['pajak_gabungan']),
                'partner_code': str(x['partner_code'].encode('ascii','ignore').decode('ascii')) if x['partner_code'] != None else '',
                'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                'date':  x['date'],
                'untaxed_amount': x['untaxed_amount'],
                'tax_amount': x['tax_amount'],
                'amount_total': x['amount_total'],
                'tgl_terbit': x['tgl_terbit'],
                'thn_penggunaan': x['thn_penggunaan'],
                'cetak_ke': x['cetak_ke'],
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
                'no': value,
                'code_pajak': value,
                'form_name': value,
                'pajak_gabungan': value,
                'partner_code':value,
                'partner_name': value,
                'date': value,
                'untaxed_amount': 0,
                'tax_amount': 0,
                'amount_total': 0,
                'tgl_terbit': value,
                'thn_penggunaan': 0,
                'cetak_ke': 0,
                'state': value,
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(wtc_report_faktur_pajak_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_faktur_pajak_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_faktur_pajak.report_faktur_pajak'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_faktur_pajak.report_faktur_pajak'
    _wrapped_report_class = wtc_report_faktur_pajak_print
    