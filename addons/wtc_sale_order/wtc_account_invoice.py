import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp


class wtc_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def _register_hook(self, cr):
        selection = self._columns['tipe'].selection
        if ('md_sale_unit', 'md_sale_unit') and ('md_sale_sparepart', 'md_sale_sparepart') and ('blind_bonus_jual', 'blind_bonus_jual') not in selection:
            self._columns['tipe'].selection.append(
                ('md_sale_unit', 'md_sale_unit'))
            self._columns['tipe'].selection.append(
                ('md_sale_sparepart', 'md_sale_sparepart'))
            self._columns['tipe'].selection.append(
                ('blind_bonus_jual', 'blind_bonus_jual'))
            
        return super(wtc_account_invoice, self)._register_hook(cr)
    
    def _get_branch_journal_config_so(self,branch_id):
        result = {}
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning( ("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu"))
        else:
            if not(obj_branch_config.wtc_so_account_discount_cash_id and obj_branch_config.wtc_so_account_discount_program_id and obj_branch_config.wtc_so_account_discount_lainnya_id and obj_branch_config.wtc_so_account_discount_cash_sparepart_id and obj_branch_config.wtc_so_account_discount_cash_oil_id):
                raise Warning( ("Konfigurasi cabang jurnal Diskon belum dibuat, silahkan setting dulu"))
        result.update({
                  'wtc_so_account_discount_cash_id':obj_branch_config.wtc_so_account_discount_cash_id,
                  'wtc_so_account_discount_program_id':obj_branch_config.wtc_so_account_discount_program_id,
                  'wtc_so_account_discount_lainnya_id':obj_branch_config.wtc_so_account_discount_lainnya_id,
                  'wtc_so_account_discount_cash_sparepart_id': obj_branch_config.wtc_so_account_discount_cash_sparepart_id,
                  'wtc_so_account_discount_cash_oil_id': obj_branch_config.wtc_so_account_discount_cash_oil_id,
                  })
        
        return result
    
    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(wtc_account_invoice,self).finalize_invoice_move_lines(move_lines)
        if self.type=='out_invoice' and self.tipe =='md_sale_unit':
            
            if self.discount_cash>0 or self.discount_lain>0 or self.discount_program>0:
                move_lines.pop()
                journal_config = self._get_branch_journal_config_so(self.branch_id.id)
                period_ids = self.env['account.period'].find(dt=self._get_default_date().date())
                move_obj = self.env['account.move']
                
                move_lines.append((0,0,{
                               'name': self.name,
                                'partner_id': self.partner_id.id,
                                'account_id': self.account_id.id,
                                'period_id': period_ids.id,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'debit': self.amount_total,
                                'credit': 0.0,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))
                
                if self.discount_cash>0:
                    
                    move_lines.append((0,0,{
                               'name': 'Diskon Cash '+ self.name,
                               'ref' : 'Diskon Cash '+ self.name, 
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_so_account_discount_cash_id'].id,
                                'period_id': period_ids.id,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'debit': self.discount_cash,
                                'credit': 0.0,                                
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))
                    
                if self.discount_program>0:
                    move_lines.append((0,0,{
                                'name': 'Diskon Program '+ self.name,
                                'ref' : 'Diskon Program '+ self.name,
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_so_account_discount_program_id'].id,
                                'period_id': period_ids.id,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'debit': self.discount_program,
                                'credit': 0.0,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                                
                        }))
    
                    
                if self.discount_lain>0:
                    move_lines.append((0,0,{
                               'name': 'Diskon Cash '+ self.name,
                               'ref': 'Diskon Cash '+ self.name,
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_so_account_discount_lainnya_id'].id,
                                'period_id': period_ids.id,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'debit': self.discount_lain,
                                'credit': 0.0,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))

        if self.type=='out_invoice' and self.tipe =='md_sale_sparepart':
            
            if self.discount_cash>0:
                move_lines.pop()
                journal_config = self._get_branch_journal_config_so(self.branch_id.id)
                period_ids = self.env['account.period'].find(dt=self._get_default_date().date())
                move_obj = self.env['account.move']
                
                move_lines.append((0,0,{
                               'name': self.name,
                                'partner_id': self.partner_id.id,
                                'account_id': self.account_id.id,
                                'period_id': period_ids.id,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'debit': self.amount_total,
                                'credit': 0.0,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))
                
                if self.discount_cash>0:
                    part = []
                    oil = []
                    for line in self.invoice_line:
                        if line.product_id.categ_id.name in ('OIL','NONHGP-FEDERAL','GMO'):
                            oil.append(line.price_subtotal)
                        else:
                            part.append(line.price_subtotal)
                    if round(sum(x for x in part),2)==0.00:
                        move_lines.append((0,0,{
                                   'name': 'Diskon Cash '+ self.name,
                                   'ref' : 'Diskon Cash '+ self.name, 
                                    'partner_id': self.partner_id.id,
                                    'account_id': journal_config['wtc_so_account_discount_cash_oil_id'].id,
                                    'period_id': period_ids.id,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'debit': self.discount_cash,
                                    'credit': 0.0,                                
                                    'branch_id': self.branch_id.id,
                                    'division': self.division,
                            }))
                    elif round(sum(x for x in part),2)==0.00:
                        move_lines.append((0,0,{
                                   'name': 'Diskon Cash '+ self.name,
                                   'ref' : 'Diskon Cash '+ self.name, 
                                    'partner_id': self.partner_id.id,
                                    'account_id': journal_config['wtc_so_account_discount_cash_sparepart_id'].id,
                                    'period_id': period_ids.id,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'debit': self.discount_cash,
                                    'credit': 0.0,                                
                                    'branch_id': self.branch_id.id,
                                    'division': self.division,
                            }))
                    else:
                        move_lines.append((0,0,{
                                   'name': 'Diskon Cash '+ self.name,
                                   'ref' : 'Diskon Cash '+ self.name, 
                                    'partner_id': self.partner_id.id,
                                    'account_id': journal_config['wtc_so_account_discount_cash_sparepart_id'].id,
                                    'period_id': period_ids.id,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'debit': (self.discount_cash*sum(x for x in part))/sum(x for x in part)+sum(x for x in oil),
                                    'credit': 0.0,                                
                                    'branch_id': self.branch_id.id,
                                    'division': self.division,
                            }))
                        move_lines.append((0,0,{
                                   'name': 'Diskon Cash '+ self.name,
                                   'ref' : 'Diskon Cash '+ self.name, 
                                    'partner_id': self.partner_id.id,
                                    'account_id': journal_config['wtc_so_account_discount_cash_oil_id'].id,
                                    'period_id': period_ids.id,
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'debit': (self.discount_cash*sum(x for x in oil))/sum(x for x in part)+sum(x for x in oil),
                                    'credit': 0.0,                                
                                    'branch_id': self.branch_id.id,
                                    'division': self.division,
                            }))
                    
                
               
        return move_lines