from openerp import models, fields, api

class wtc_faktur_pajak(models.Model):
    _inherit = 'wtc.faktur.pajak.out'

    def _report_xls_faktur_pajak_fields(self, cr, uid, context=None):
        return [
            'no',\
            'code_pajak',\
            'form_name',\
            'pajak_gabungan',\
            'partner_code',\
            'partner_name',\
            'date',\
            'tgl_terbit',\
            'thn_penggunaan',\
            'cetak_ke',\
            'state',\
            'untaxed_amount',\
            'tax_amount',\
            'amount_total',\
        ]
        
class wtc_generate_faktur_pajak(models.Model):
    _inherit = 'wtc.faktur.pajak'

    def _report_xls_generate_faktur_pajak_fields(self, cr, uid, context=None):
        return [
            'no',\
            'gfp_name',\
            'gfp_no_document',\
            'pajak_total',\
        ]    
        
    def _report_xls_generate_faktur_pajak_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'gfp_name',\
            'gfp_no_document',\
            'gfp_date',\
            'gfp_thn',\
            'gfp_tgl_terbit',\
            'gfp_counter_start',\
            'gfp_counter_end',\
            'gfp_prefix',\
            'gfp_padding',\
            'state',\
            'fp_code',\
            'fp_state',\
            'pajak_total',\
        ]  
        
class wtc_faktur_pajak_gabungan(models.Model):
    _inherit = 'wtc.faktur.pajak.gabungan'

    def _report_xls_faktur_pajak_gabungan_fields(self, cr, uid, context=None):
        return [
            'no',\
            'transaction_ref',\
            'partner_name',\
            'sum_tax_amount',\
            'sum_untaxed_amount',\
            'sum_total_amount',\
            
        ]    
        
    def _report_xls_faktur_pajak_gabungan_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'transaction_ref',\
            'branch_code',\
            'division',\
            'code_pajak',\
            'date',\
            'start_date',\
            'end_date',\
            'partner_code',\
            'partner_name',\
            'tgl_document',\
            'state',\
            'transaction_no',\
            'sum_tax_amount',\
            'sum_untaxed_amount',\
            'sum_total_amount',\
        ]          
        
class wtc_faktur_pajak_others(models.Model):
    _inherit = 'wtc.faktur.pajak.other'

    def _report_xls_faktur_pajak_others_fields(self, cr, uid, context=None):
        return [
            'no',\
            'reference',\
            'no_faktur',\
            'partner_code',\
            'partner_name',\
            'date',\
            'pajak_gabungan',\
            'thn_penggunaan',\
            'tgl_terbit',\
            'no_kwitansi',\
            'untaxed_amount',\
            'tax_amount',\
            'amount_total',\
            'state',\
        ] 
        
class wtc_regenerate_faktur_pajak(models.Model):
    _inherit = 'wtc.regenerate.faktur.pajak.gabungan'

    def _report_xls_regenerate_faktur_pajak_fields(self, cr, uid, context=None):
        return [
            'no',\
            'ref',\
            'form_name',\
            'sum_tax_amount',\
            'sum_untaxed_amount',\
            'sum_total_amount',\
        ]    
        
    def _report_xls_regenerate_faktur_pajak_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'ref',\
            'form_name',\
            'date',\
            'state',\
            'transaction_no',\
            'no_faktur',\
            'partner_code',\
            'partner_name',\
            'sum_tax_amount',\
            'sum_untaxed_amount',\
            'sum_total_amount',\
            'total_line',\
        ]         
               