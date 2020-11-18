from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_generate_faktur_pajak_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_generate_faktur_pajak_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        thn_penggunaan = data['thn_penggunaan']
        state_generate_faktur_pajak = data['state_generate_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        
        where_thn_penggunaan = " 1=1 "
        if thn_penggunaan :
            where_thn_penggunaan = " gfp.thn_penggunaan = '%s'" % str(thn_penggunaan)
            
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " gfp.date >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " gfp.date <= '%s'" % str(end_date)
            
        where_state_generate_faktur_pajak = " 1=1 "
        if state_generate_faktur_pajak  :
            where_state_generate_faktur_pajak = " gfp.state = '%s'" % str(state_generate_faktur_pajak)
        
        query_generate_faktur_pajak = """
            select gfp.id as gfp_id,
            gfp.name as gfp_name,
            gfp.no_document as gfp_no_document,
            gfp.date as gfp_date,
            gfp.thn_penggunaan as gfp_thn,
            gfp.tgl_terbit as gfp_tgl_terbit,
            gfp.counter_start as gfp_counter_start,
            gfp.counter_end as gfp_counter_end,
            gfp.prefix as gfp_prefix,
            gfp.padding as gfp_padding,
            gfp.state as state,
            pajak.total as pajak_total,
            fp.name as fp_code,
            fp.state as fp_state
            from wtc_faktur_pajak gfp
            inner join wtc_faktur_pajak_out fp on fp.faktur_pajak_id = gfp.id 
            left join (select faktur_pajak_id,count(id) as total from wtc_faktur_pajak_out group by faktur_pajak_id) pajak on pajak.faktur_pajak_id = gfp.id           
        """
        
        where = "WHERE " + where_thn_penggunaan + " AND " + where_state_generate_faktur_pajak + " AND " + where_start_date + " AND " + where_end_date
        order = "order by gfp.name,gfp.date"
        self.cr.execute(query_generate_faktur_pajak + where + order)
        all_lines = self.cr.dictfetchall()
        pajak = []
        if all_lines != [] and len(all_lines) < 65000:
            datas = map(lambda x : {
                'gfp_id': x['gfp_id'],
                'no': 0,
                'gfp_name': str(x['gfp_name'].encode('ascii','ignore').decode('ascii')) if x['gfp_name'] != None else '',
                'gfp_no_document': str(x['gfp_no_document'].encode('ascii','ignore').decode('ascii')) if x['gfp_no_document'] != None else '',
                'gfp_date': str(x['gfp_date'].encode('ascii','ignore').decode('ascii')) if x['gfp_date'] != None else '',
                'gfp_thn': x['gfp_thn'],
                'gfp_tgl_terbit': str(x['gfp_tgl_terbit'].encode('ascii','ignore').decode('ascii')) if x['gfp_tgl_terbit'] != None else '',
                'gfp_counter_start': x['gfp_counter_start'],
                'gfp_counter_end':  x['gfp_counter_end'],
                'gfp_prefix': str(x['gfp_prefix']),
                'gfp_padding': x['gfp_padding'],
                'state':str(x['state']),
                'pajak_total': x['pajak_total'],
                'fp_code': str(x['fp_code'].encode('ascii','ignore').decode('ascii')) if x['fp_code'] != None else '',
                'fp_state': str(x['fp_state'].encode('ascii','ignore').decode('ascii')) if x['fp_state'] != None else '',
                }, all_lines)
            for p in datas:
                if p['gfp_id'] not in map(lambda x: x.get('gfp_id', None), pajak):
                    pajak.append(p)
                    pajak_lines = filter(lambda x: x['gfp_id'] == p['gfp_id'], all_lines)
                    p.update({'lines': pajak_lines})     
            reports = filter(lambda x: pajak, [{'pajak': pajak}])
        else :
            value = False
            if len(all_lines) > 65000 :
                value = 'OVER LOAD'
            else :
                value = 'NO DATA FOUND'
            reports = [{'pajak': [{
                                'gfp_id': value,
                                'no': value,
                                'gfp_name': value,
                                'gfp_no_document': value,
                                'gfp_date': value,
                                'gfp_thn':0,
                                'gfp_tgl_terbit': value,
                                'gfp_counter_start': 0,
                                'gfp_counter_end': 0,
                                'gfp_prefix': 0,
                                'gfp_padding': 0,
                                'state':value,
                                'pajak_total': 0,
                                'fp_code': value,
                                'fp_state': value,
                                'lines':[{
                                        'gfp_id': value,
                                        'no': value,
                                        'gfp_name': value,
                                        'gfp_no_document': value,
                                        'gfp_date': value,
                                        'gfp_thn':0,
                                        'gfp_tgl_terbit': value,
                                        'gfp_counter_start': 0,
                                        'gfp_counter_end': 0,
                                        'gfp_prefix': 0,
                                        'gfp_padding': 0,
                                        'pajak_total': 0,
                                        'state':value,
                                        'fp_code': value,
                                        'fp_state': value}]
                    }]}]
        self.localcontext.update({'reports': reports})
        super(wtc_report_generate_faktur_pajak_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_generate_faktur_pajak_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_faktur_pajak.report_generate_faktur_pajak'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_faktur_pajak.report_generate_faktur_pajak'
    _wrapped_report_class = wtc_report_generate_faktur_pajak_print
    