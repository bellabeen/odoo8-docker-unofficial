from openerp import models, fields, api

class wtc_branch_config(models.Model):
    _inherit = "account.journal"
    
    is_pusted = fields.Boolean('Sudah PUST?',default=True)
    
    @api.multi
    def action_check_pust(self):
        journals = self.env['account.journal'].search([('type','=','cash'),('is_pusted','=',True)])
        for journal in journals:
            query = """
                SELECT 
                    CASE WHEN sum(debit)-sum(credit) IS NULL THEN 0.0 
                    ELSE sum(debit)-sum(credit)  
                    END  as balance
                FROM  account_move_line WHERE account_id = %d
            """ %(journal.default_debit_account_id.id)
            self._cr.execute(query)
            balance = self._cr.dictfetchall()[0].get('balance',False)
            if journal.default_debit_account_id and round(balance,2)!=0:
                journal.write({'is_pusted': False})
        
                
