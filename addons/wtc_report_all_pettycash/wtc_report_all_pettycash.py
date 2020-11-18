from openerp import models, fields, api

class wtc_pettycash_out(models.Model):
    _inherit = 'wtc.pettycash'

    def _report_xls_pettycash_out_fields(self, cr, uid, context=None):
        return [
            'no',\
            'pco_name',\
            'branch_code',\
            'sum_total_amount',\
            'sum_amount_real',\
            
        ]    
        
    def _report_xls_pettycash_out_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'pco_name',\
            'branch_code',\
            'branch_destination_code',\
            'pco_division',\
            'pco_date',\
            'journal_name',\
            'partner_name',\
            'line_name',\
            'sum_total_amount',\
            'sum_amount_real',\
            'pco_state',\
        ]          
        
class wtc_pettycash_in(models.Model):
    _inherit = 'wtc.pettycash.in'

    def _report_xls_pettycash_in_fields(self, cr, uid, context=None):
        return [
            'no',\
            'pci_name',\
            'branch_code',\
            'pco_name',\
            'sum_total_amount',\
            
        ]    
        
    def _report_xls_pettycash_in_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'pci_name',\
            'branch_code',\
            'branch_destination_code',\
            'pci_division',\
            'pci_date',\
            'pco_name',\
            'journal_name',\
            'line_name',\
            'sum_total_amount',\
            'pci_state',\
        ]   
        
class wtc_reimburse(models.Model):
    _inherit = 'wtc.reimbursed'

    def _report_xls_reimbursed_fields(self, cr, uid, context=None):
        return [
            'no',\
            'r_name',\
            'branch_code',\
            'sum_total_amount',\
            
        ]    
        
    def _report_xls_reimbursed_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'r_name',\
            'branch_code',\
            'r_division',\
            'date_request',\
            'date_approve',\
            'date_cancel',\
            'line_name',\
            'line_date',\
            'branch_destination',\
            'sum_total_amount',\
            'r_state',\
        ]      
        
class wtc_bank_transfer(models.Model):
    _inherit = 'wtc.bank.transfer'

    def _report_xls_bank_transfer_fields(self, cr, uid, context=None):
        return [
            'no',\
            'bt_name',\
            'branch_code',\
            'sum_total_amount',\
            
        ]    
        
    def _report_xls_bank_transfer_detail_fields(self, cr, uid, context=None):
        return [
            'no',\
            'bt_name',\
            'branch_code',\
            'bt_division',\
            'bt_date',\
            'reimburse_ref',\
            'line_name',\
            'sum_total_amount',\
            'bt_state',\
        ]    