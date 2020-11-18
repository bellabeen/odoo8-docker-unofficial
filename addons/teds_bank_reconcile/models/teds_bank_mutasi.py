import time
from openerp.osv import fields, osv
from openerp import api, fields, models
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare
from openerp.exceptions import Warning
from datetime import date, datetime, timedelta
import datetime
from openerp import SUPERUSER_ID
import base64
import xlrd

class TedsBankMutasi(models.Model):
    _name = "teds.bank.mutasi"
    _description = 'Bank Mutasi'
    
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()


    name = fields.Char(string='Name')
    remark = fields.Char(string="Remark")
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    amount = fields.Float(string='Amount')
    saldo = fields.Float(string='Saldo')
    date = fields.Date('Date')
    time = fields.Char('Time')
    teller = fields.Char('Teller')
    coa = fields.Char('COA')
    no_sistem = fields.Char('No Sistem')
    account_id = fields.Many2one('account.account',string='Account')
    journal_id = fields.Many2one('account.journal',string='Journal')
    format = fields.Selection([
                              ('bca','BCA'),
                              ('bri','BRI'),
                              ('bni','BNI'),
                              ('mandiri','Mandiri'),
                              ('update','Update Bank Mutasi'),
                              ],string='Format')
    date_upload= fields.Date('Tanggal Upload',default=_get_default_date)
    bank_reconcile_id=fields.Many2one('teds.bank.reconcile','Bank Reconcile') 
    reconciled = fields.Boolean('Reconciled',default=False)
    state = fields.Selection([
                              ('Outstanding','Outstanding'),
                              ('Reconciled','Reconciled'),
                              ('Auto Reconcile','Auto Reconcile'),
                              ],string='State',default='Outstanding')
    branch_id = fields.Many2one('wtc.branch','Branch')
    effective_date_reconcile = fields.Date('Effective Date Reconcile')
    checked = fields.Boolean('Checked',default=False)
    is_posted = fields.Boolean('Auto Posted ?')

    @api.model
    def _auto_init(self):
        res = super(TedsBankMutasi, self)._auto_init()
        self._cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'teds_bank_mutasi_branch_date_no_sistem_index'")
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX teds_bank_mutasi_branch_date_no_sistem_index ON teds_bank_mutasi  USING btree (branch_id,date,no_sistem)')
        return res

    @api.model
    def create(self,vals):
        credit = 0
        debit = 0
        name = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'BM')
        if vals.get('credit'):
            credit = float(vals['credit'])
            vals['debit'] = 0
        if vals.get('debit'):
            debit = float(vals['debit'])
            vals['credit'] = 0
        amount = debit + credit
        vals['amount'] = amount
        if vals.get('date'):
            vals['name'] = name
        return super(TedsBankMutasi,self).create(vals)

    @api.multi
    def button_reconcile(self):
       self.auto_reconcile_scheduled()

    @api.multi
    def auto_reconcile_scheduled(self):
        datas = self.search([('state','=','Outstanding'),('no_sistem','!=',''),('checked','=',False)],limit=30)
        self.auto_reconcile(datas)


    @api.multi
    def auto_reconcile(self,datas):
        for data in datas:
            data = self.browse(data.id)
            bank_reconcile = self.env['teds.bank.reconcile']
            aml = self.env['account.move.line']
            if data:
                debit = data.debit
                credit = data.credit
                no_sistem = str(tuple(data.no_sistem.encode('utf-8').split('|'))).replace(',)',')')
                coa = data.account_id.id
                query = """
                            SELECT id, debit, credit FROM account_move_line WHERE ref IN %s AND account_id = %s
                        """%(no_sistem,coa)
                self.env.cr.execute(query)
                ress = self.env.cr.dictfetchall()
                if ress:
                    rk_balance = data.debit - data.credit
                    journal_balance = 0
                    journal_ids = []
                    for res in ress:
                        journal_ids.append(res['id'])
                        journal_balance += res['debit'] - res['credit']
                 

                    if abs(journal_balance + rk_balance) <= 10 :
                        vals = {
                            'branch_id': data.branch_id.id, 
                            'state': 'Auto Reconcile', 
                            'move_line_ids': 
                                [[6, False, journal_ids]], 
                            # 'journal_id': data.journal_id.id,
                            'account_id':data.account_id.id, 
                            'bank_mutasi_ids': [[6, False, [data.id]]],
                        }
                        bank_reconcile_id = bank_reconcile.create(vals)
                        bank_reconcile_id.confirm()
                    else:
                        data.write({'checked':True})
                else:
                    data.write({'checked':True})    
         

class ImportRekeningKoran(models.TransientModel):
    _name = "teds.import.rekening.koran"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
     
    name = fields.Char(string='Name')
    remark = fields.Char(string='Remark')
    data_file = fields.Binary(string='File')
    saldo_akhir = fields.Float(string='Saldo Akhir')
    account_id = fields.Many2one('account.account',string='Account')
    journal_id = fields.Many2one('account.journal',string='Journal',domain="[('branch_id','=',branch_id),('type','=','bank')]")
    format = fields.Selection([
                              ('bca','BCA'),
                              ('bri','BRI'),
                              ('bni','BNI'),
                              ('mandiri','Mandiri'),
                              ('update','Update Bank Mutasi'),
                              ],string='Format')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    
    # @api.onchange('branch_id')
    # def onchange_branch_id(self):
    #     branch_id = self.branch_id.id
    #     if self.journal_id.branch_id == branch_id:
    #         self.journal_id = True
    #     else:
    #         self.journal_id = False

    
    # @api.onchange('journal_id')
    # def onchange_account(self):
    #     account_src = self.env['account.account'].search([('name','=',self.journal_id.name)])
    #     if account_src:
    #         self.account_id = account_src.id


    @api.multi
    def get_saldo_akhir(self,account_id,date_max):
        total_debit=0
        total_credit=0
        bank_mutasi=self.env['teds.bank.mutasi'].search([('account_id','=',account_id),('date','=',date_max)])
        if bank_mutasi :
            for line in bank_mutasi :
                total_credit += line.credit
                total_debit += line.debit
            saldo_akhir_mutasi=total_debit-total_credit
            
            return saldo_akhir_mutasi
  
    
    @api.multi
    def check_file(self): 
        var = []
        from_file = {}
        data = base64.decodestring(self.data_file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)  
        
        total_credit_file=0
        total_debit_file =0
  
        time=False
        name=False
        no_sistem = False
        tanggal = False
        teller = False
        saldo = False
        credit = False
        debit = False
        remark = False
        coa = False
        for rx in range(1,sh.nrows): 
            if self.format == 'bri':
                tanggal=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
                time=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [1]
                remark=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [2]
                debit=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [3] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [3] else 0
                credit=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [4] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [4] else 0
                saldo=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [5]
                teller=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [6]
                coa=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [7]
                no_sistem=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [8] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [8] else ''
                total_credit_file += credit
                total_debit_file += debit
                tanggal = datetime.date(*xlrd.xldate_as_tuple(tanggal, 0)[:3])

            elif self.format == 'update':
                name=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [0]    
                tanggal=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [1] 
                remark=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [2]  
                teller=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [3]  
                debit=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [4]   
                credit=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [5]  
                saldo=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [6] 
                coa=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [7] 
                no_sistem=[sh.cell(rx,ry).value for ry in range(sh.ncols)] [8]
            
            else :
                tanggal=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
                # time=''
                remark=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [1] 
                teller=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [2]
                debit=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [3] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [3] else 0
                credit=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [4] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [4] else 0
                saldo=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [5]
                coa=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [6]
                no_sistem=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [7] if [sh.cell(rx, ry).value for ry in range(sh.ncols)] [7] else ''
                total_credit_file += credit
                total_debit_file += debit
                tanggal = datetime.date(*xlrd.xldate_as_tuple(tanggal, 0)[:3])
                
            # tanggal = datetime.date(*xlrd.xldate_as_tuple(tanggal, 0)[:3])

            var.append({
                'name':name,
                'remark':remark,
                'time':time,
                'debit':debit,
                'account_id':self.account_id.id,
                'format':self.format,
                'credit':credit,
                'saldo':saldo,
                'date':tanggal ,
                'teller':teller,
                'coa':coa,
                'no_sistem':no_sistem,
            })
        total_saldo_from_excel=total_debit_file-total_credit_file
        from_file.update({
                        'var_file':var,
                        'total_saldo_from_excel':total_saldo_from_excel,
                        })    
        return from_file   
              
    @api.multi             
    def import_excel(self):
        obj_bank = self.env['teds.bank.mutasi']

        if self.format == 'update':
            saldo_file_excel=self.check_file()
            bank_mutasi = self.env['teds.bank.mutasi']
            for x in saldo_file_excel['var_file'] :
                name = x['name'].strip()
                no_sistem = x['no_sistem'].strip()

                query = """
                            UPDATE teds_bank_mutasi SET no_sistem = '%s', checked = False WHERE name='%s' AND state = 'Outstanding'
                        """ %(no_sistem, name)
        
                self.env.cr.execute(query)
        else:       
            query_date= """
                        SELECT MAX(date) from teds_bank_mutasi
                        WHERE account_id='%s' 
                       """ % (self.account_id.id)
            self._cr.execute (query_date)
            res_max = self._cr.fetchone()
            date_max = res_max[0]
            saldo_file_excel=self.check_file()
            if date_max :
                saldo_akhir_mutasi=self.get_saldo_akhir(self.account_id.id,date_max)
                saldo_all=saldo_akhir_mutasi+saldo_file_excel['total_saldo_from_excel']
            else :
                saldo_all=self.saldo_akhir
            saldo_all = round(saldo_all,2)
            saldo_akhir = round(self.saldo_akhir,2)
            if float_compare(saldo_all, saldo_akhir, precision_digits=2) == 1:
                raise Warning(_('Saldo akhir tidak sesuai.\n'
                    'Saldo di system %s, saldo yang diinput %s') % (saldo_all, saldo_akhir))
            for x in saldo_file_excel['var_file'] :
                mutasi = {
                    'remark':x['remark'],
                    'time':x['time'],
                    'debit':x['debit'],
                    'account_id':self.account_id.id,
                    'format':self.format,
                    'credit':x['credit'],
                    'saldo':x['saldo'],
                    'date':x['date'],     
                    'teller':x['teller'], 
                    'coa':x['coa']   ,
                    'no_sistem':x['no_sistem'].strip(),
                    'journal_id': self.journal_id.id,
                    'branch_id':self.branch_id.id    
                }
                create=obj_bank.create(mutasi)


    
class TedsAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    #no_reconcile_rk=fields.Many2one('teds.bank.mutasi','No Reconcile')
    teds_bank_reconcile_id = fields.Many2one('teds.bank.reconcile','Bank Reconcile',copy=False) 
    teds_reconciled_rk = fields.Boolean('Reconciled',default=False,copy=False)
    effective_date_reconcile = fields.Date('Effective Date Reconcile',copy=False)
