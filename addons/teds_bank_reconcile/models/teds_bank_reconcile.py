import time
from openerp.osv import fields, osv
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import date, datetime, timedelta
import datetime
from openerp import SUPERUSER_ID
import base64
import xlrd
    
class TedsBankReconcile(models.Model):
    _name = "teds.bank.reconcile"
    _description = 'Bank Reconcile'

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()
    
    name = fields.Char(string='Name')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    move_line_ids=fields.Many2many('account.move.line', 'teds_bank_reconcile_rel', 'teds_bank_reconcile_id',
                                        'line_id', 'Move Line', copy=False)                               
    bank_mutasi_ids = fields.Many2many("teds.bank.mutasi",'bank_mutasi_rel', 'bank_mutasi_id',
                                        'mutasi_bank_id', 'Mutasi Id', copy=False)       
    # journal_id = fields.Many2one('account.journal',string='Journal',domain="[('branch_id','=',branch_id),('type','=','bank')]")
    account_id = fields.Many2one('account.account',string='Account',domain="[('type','=','liquidity'),('branch_id','=',branch_id)]")

    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ('Auto Reconcile','Auto Reconcile'),
                              ('cancel','Cancelled')
                              ],string='State',default='draft')
    date= fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    effective_date_reconcile = fields.Date('Effective Date Reconcile')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime(string="Cancelled on")
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'BRM')
        values['date'] = self._get_default_date()
        return super(TedsBankReconcile, self).create(values)
    
    @api.multi
    def unlink(self, context=None):
        for tc in self :
            if tc.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(TedsBankReconcile, self).unlink()
    
    
    @api.model
    def copy(self):
        raise Warning('Transaksi ini tidak dapat diduplikat.')
        return super(TedsBankReconcile, self).copy()
    
    
    @api.multi
    def check_move_line(self):
        total_debit=0
        total_credit=0
        ids = []
        effective_date = str(date.min)
        for move_line in self.move_line_ids :
            if move_line.teds_reconciled_rk == True :
                raise Warning('Maaf, Account %s sudah di reconcile'%(move_line.ref))
            if move_line.date > effective_date:
                effective_date = move_line.date
            ids.append(move_line.id)
            total_credit += move_line.credit
            total_debit += move_line.debit
        saldo_akhir_mutasi=total_debit-total_credit
        return (ids, effective_date, saldo_akhir_mutasi)
    
    @api.multi
    def check_mutasi(self):
        total_debit=0
        total_credit=0
        effective_date = str(date.min)
        ids = []
        for lines_mutasi in self.bank_mutasi_ids :
            if lines_mutasi.reconciled == True :
                raise Warning('Maaf, No Sistem %s sudah di reconcile'%(lines_mutasi.no_sistem))
            if lines_mutasi.date > effective_date:
                effective_date = lines_mutasi.date
            ids.append(lines_mutasi.id)
            total_credit += lines_mutasi.credit
            total_debit += lines_mutasi.debit
        saldo_akhir_mutasi=total_debit-total_credit
        return (ids, effective_date, saldo_akhir_mutasi)
    
    @api.multi
    def confirm(self):
        if not self.move_line_ids:
            raise Warning('Detail Journal tidak boleh kosong !')

        if not self.bank_mutasi_ids and not self.move_line_ids :
            raise Warning('Line belum diisi')

        move_line_ids, eff_date1, move_line_saldo=self.check_move_line()
        mutasi_ids, eff_date2, mutasi_saldo=self.check_mutasi()
        effective_date = max(eff_date1, eff_date2)
        if effective_date == date.min:
            effective_date = self._get_default_date()

        if self.bank_mutasi_ids or self.move_line_ids:
            if abs(move_line_saldo + mutasi_saldo) <= 10:
                self.move_line_ids.write({'teds_reconciled_rk':True,'teds_bank_reconcile_id':self.id,'effective_date_reconcile':effective_date})
                self.bank_mutasi_ids.write({'state':'Reconciled','reconciled':True,'bank_reconcile_id':self.id,'effective_date_reconcile':effective_date})

                if self.state == 'Auto Reconcile':
                    self.write({'confirm_date': self._get_default_datetime(),'effective_date_reconcile':effective_date})
                else :
                    self.write({'state': 'posted','confirm_uid':self._uid,'confirm_date': self._get_default_datetime(),'effective_date_reconcile':effective_date})
            else:
                raise Warning('Saldo bank mutasi dan sistem tidak sesuai.\n Saldo bank %s, saldo sistem %s'%(mutasi_saldo, move_line_saldo))

        else :
            raise Warning('Saldo bank mutasi dan sistem tidak sesuai.\n Saldo bank %s, saldo sistem %s'%(mutasi_saldo, move_line_saldo))
    
    @api.onchange('branch_id')
    def onchange_branch(self):
        self.account_id = False
    
    
    @api.onchange('account_id')
    def onchange_account_id(self):
        account_id = self.account_id.id
        if self.bank_mutasi_ids:
            for bank_mutasi_id in self.bank_mutasi_ids:
                if bank_mutasi_id.account_id != account_id:
                    self.bank_mutasi_ids = False
        if self.move_line_ids:
            for move_line_id in self.move_line_ids:
                if move_line_id.account_id != account_id:
                    self.move_line_ids = False 
