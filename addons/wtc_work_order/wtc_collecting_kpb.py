import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning


class wtc_collecting_kpb(models.Model):
    _name = "wtc.collecting.kpb"
    _description = 'Collecting KPB'
    _order = "date desc"
    
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
    
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    @api.one
    @api.depends('due_date')
    def _compute_due_date_show(self):
        self.due_date_show = self.due_date

    name = fields.Char('Collecting KPB', size=64, readonly=True)
    branch_id = fields.Many2one('wtc.branch','Branch',required=True, default=_get_default_branch)
    division = fields.Selection([('Sparepart','Sparepart')],'Division', change_default=True,select=True,required=True,default='Sparepart')
    work_order_ids =  fields.One2many('wtc.work.order','collecting_id')
    state =  fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], 'State', readonly=True, default='draft')
    supplier_id = fields.Many2one('res.partner','Supplier',required=True)
    collecting_line = fields.One2many('wtc.collecting.kpb.line','collecting_id')
    supplier_ref = fields.Char(string='No. Claim MD',size=64)
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    date  =  fields.Date('Date',default=_get_default_date)
    type =  fields.Selection([('CLA','Claim'),('KPB','KPB')],string='Type')
    start_date  =  fields.Date(string='Start Date')
    end_date  =  fields.Date(string='End Date')
    due_date = fields.Date('Due Date')
    due_date_show = fields.Date('Due Date',compute="_compute_due_date_show",readonly=True)
    amount = fields.Float(string='Amount')
    
    
    @api.model
    def create(self,values,context=None):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'CK')
        collecting_kpb = super(wtc_collecting_kpb,self).create(values)
        return collecting_kpb 
    
    
    @api.multi
    def write(self, values):
        if 'work_order_ids' not in values :
            for key in values :
                if key in ('branch_id', 'type', 'start_date', 'end_date') :
                    values.update({'work_order_ids': [(5,0)],'collecting_line': [(5,0)], 'amount': 0})
                    break
        return super(wtc_collecting_kpb, self).write(values)
    
    
    @api.multi
    def unlink(self, context=None):
        for tc in self :
            if tc.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(wtc_collecting_kpb, self).unlink()
    
    @api.model
    def copy(self):
        raise Warning('Transaksi ini tidak dapat diduplikat.')
        return super(wtc_collecting_kpb, self).copy()
    
    
    @api.multi
    def action_get_detail(self):
        wo = []   
        query = """ 
                select wo.id
                from wtc_work_order wo 
                inner join account_invoice ai on wo.id = ai.transaction_id and ai.type = 'out_invoice' and ai.model_id in (select id from ir_model where model='wtc.work.order')
                inner join account_move_line aml on aml.move_id=ai.move_id and aml.debit > 0 and ai.account_id= aml.account_id and ai.journal_id=aml.journal_id
                WHERE 
                wo.branch_id = %s
                and wo.collecting_id IS NULL
                and wo.state='open'
                and wo.kpb_collected='ok'
                and wo.type='%s'
                and wo.date>='%s'
                and wo.date<='%s'
                and aml.reconcile_id IS NULL
                and aml.reconcile_partial_id IS NULL
        """%(self.branch_id.id,self.type, self.start_date,self.end_date)
        self._cr.execute (query)
        ress = self._cr.fetchall()
        if ress :
            for res in ress:
                wo.append(res[0])
            self.write({'work_order_ids': [(6,0,wo)]})
            self.get_rekap_collecting_line()
        else :
            raise Warning('Data Tidak diTemukan')
                    
            
        
    @api.multi  
    def get_rekap_collecting_line(self) :
        wo=[]
        collecting = []
        amount = 0.0
        for x in self.work_order_ids :
            wo.append(x.id)
        if wo :  
            if self.type == 'KPB':
                query = """
                        SELECT  
                        wo_inv.kpb_ke,
                        wo_inv.qty,
                        COALESCE(wo_jasa.total_jasa,0) AS total_jasa ,
                        COALESCE(wo_jasa.total_oli,0) AS total_oli
                        FROM  (
                        SELECT wo.kpb_ke as kpb_ke ,COUNT(wo.id) as qty,wo.branch_id
                        FROM wtc_work_order wo
                        WHERE wo.id in %s 
                        and wo.kpb_collected='ok' and wo.state='open' 
                        GROUP BY wo.kpb_ke,wo.branch_id) AS wo_inv
                        
                        FULL OUTER JOIN
                        (SELECT wo.kpb_ke,wo.branch_id,
                        COALESCE(SUM(CASE WHEN wol.categ_id = 'Service'   THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100)*wol.product_qty  END),0) total_jasa,
                        COALESCE(SUM(CASE WHEN wol.categ_id = 'Sparepart'   THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100)*wol.supply_qty END),0) total_oli
                        
                        FROM wtc_work_order wo
                        INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                        WHERE wo.id in %s  and wo.kpb_collected='ok' and wo.state='open'  GROUP BY wo.kpb_ke,wo.branch_id) AS wo_jasa
                        
                        ON wo_inv.branch_id = wo_jasa.branch_id
                        AND  wo_inv.kpb_ke = wo_jasa.kpb_ke
                        where 1=1 
                """ %(str(tuple(wo)).replace(',)', ')'),str(tuple(wo)).replace(',)', ')') )
            else :
                query = """
                        SELECT  
                        wo_inv.qty,
                        COALESCE(wo_jasa.total_jasa,0) AS total_jasa ,
                        COALESCE(wo_jasa.total_oli,0) AS total_oli
                        FROM  (
                        SELECT COUNT(wo.id) as qty,wo.branch_id
                        FROM wtc_work_order wo
                        WHERE wo.id in %s 
                        and wo.kpb_collected='ok' and wo.state='open' 
                        GROUP BY wo.branch_id) AS wo_inv
                        
                        FULL OUTER JOIN
                        (SELECT wo.branch_id,
                        COALESCE(SUM(CASE WHEN wol.categ_id = 'Service'   THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100)*wol.product_qty  END),0) total_jasa,
                        COALESCE(SUM(CASE WHEN wol.categ_id = 'Sparepart'   THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100)*wol.supply_qty END),0) total_oli
                        
                        FROM wtc_work_order wo
                        INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                        WHERE wo.id in %s  and wo.kpb_collected='ok' and wo.state='open'  GROUP BY wo.branch_id) AS wo_jasa
                        ON wo_inv.branch_id = wo_jasa.branch_id
                        where 1=1 
                """ %(str(tuple(wo)).replace(',)', ')'),str(tuple(wo)).replace(',)', ')'))
                
            self._cr.execute (query)
            picks = self._cr.dictfetchall()
        
            if picks :
                for value in picks :
                    amount += value['total_jasa'] + value['total_oli']
                    collecting.append([0,False,value])
                self.write({'collecting_line':collecting,'amount': amount})
            else :
                raise Warning('Detail Sudah Tidak Ada.')
            
    @api.multi
    def _get_branch_journal_config(self,branch_id):
        result = {}
        branch_journal_id = self.env['wtc.branch.config'].search([('branch_id','=',branch_id)])
        if not branch_journal_id.wo_collecting_kpb_journal_id.id :
            raise Warning ('Journal Collecting KPB Belum di Setting')
        if not branch_journal_id.wo_collecting_kpb_journal_id.default_debit_account_id.id :
            raise Warning ('Journal Account Collecting KPB Belum di Setting')
        if not branch_journal_id.wo_collecting_claim_journal_id.id :
            raise Warning ('Journal Collecting Claim Belum di Setting')
        if not branch_journal_id.wo_collecting_claim_journal_id.default_debit_account_id.id :
            raise Warning ('Journal Account Collecting Claim Belum di Setting')

        journal_id=branch_journal_id.wo_collecting_kpb_journal_id.id
        account_id=branch_journal_id.wo_collecting_kpb_journal_id.default_debit_account_id.id

        if self.type == 'CLA':
            journal_id = branch_journal_id.wo_collecting_claim_journal_id.id
            account_id = branch_journal_id.wo_collecting_claim_journal_id.default_debit_account_id.id
        
        result.update({
            'journal_id':journal_id,
            'account_id':account_id,
        })
        return result
    
    
    @api.multi 
    def invoice_create(self):
        self.ensure_one()
        
        if not self.collecting_line :
            raise Warning('Detail Sudah Tidak Ada.')
        
        today = self._get_default_date()
        period_id = self.env['account.period'].find(today).id
        journal_config = self._get_branch_journal_config(self.branch_id.id) 
        move_id =  self.env['account.move'].sudo().create({
            'journal_id': journal_config['journal_id'],
            'line_id': [],
            'period_id': period_id,
            'date': today,
            'name': self.name,
            'ref': self.name
            })

        oli_total=0
        jasa_total=0
        for x in self.collecting_line:
            oli_total += x.total_oli
            jasa_total += x.total_jasa
        if oli_total > 0 :
            aml_oil = self.env['account.move.line'].sudo().create({
            'move_id':  move_id.id,
            'debit': oli_total,
            'credit':0,
            'name': self.name+' OLI',
            'ref': self.name,
            'account_id': journal_config['account_id'],
            'partner_id': self.supplier_id.id,
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_maturity':self.due_date,
        })
        if jasa_total > 0 :   
            aml_jasa = self.env['account.move.line'].sudo().create({
                'move_id':  move_id.id,
                'debit': jasa_total,
                'credit':0,
                'name': self.name+' JASA',
                'ref': self.name,
                'account_id': journal_config['account_id'],
                'partner_id': self.supplier_id.id,
                'branch_id': self.branch_id.id,
                'division': self.division,
                'date_maturity':self.due_date,
            })

        query = """
                select aml.id,aml.account_id,aml.debit,aml.branch_id,aml.partner_id,aml.division,wo.name as wo_name
                from wtc_work_order wo 
                inner join account_invoice ai on wo.id = ai.transaction_id and ai.type = 'out_invoice' and ai.model_id in (select id from ir_model where model='wtc.work.order')
                inner join account_move_line aml on aml.move_id=ai.move_id and aml.debit > 0 and ai.account_id= aml.account_id and ai.journal_id=aml.journal_id
                WHERE wo.collecting_id = %s
                and aml.reconcile_id IS NULL
                and aml.reconcile_partial_id IS NULL
            """ % (self.ids[0])
        self._cr.execute (query)
        ress = self._cr.dictfetchall()
        rec_ids = []
        for res in ress :
            aml_new = self.env['account.move.line'].sudo().create({
                'move_id': move_id.id,
                'debit': 0,
                'credit':res['debit'],
                'name': res['wo_name'],
                'ref': self.name,
                'account_id': res['account_id'],
                'partner_id': res['partner_id'],
                'branch_id': res['branch_id'],
                'division': res['division'],
            })
            rec_ids.append([res['id'], aml_new.id])
        for rec_id in rec_ids :
            self.pool.get('account.move.line').reconcile(self._cr, SUPERUSER_ID, rec_id)
        self.write({
            'state':'posted',
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_date(),
        })
            
    @api.multi
    def invoice_done(self):
        return True
   
    @api.onchange('branch_id', 'type', 'start_date', 'end_date')
    def _onchange_branch_type_date(self):
        self.work_order_ids = False
        self.collecting_line= False
        self.due_date = False
        self.amount = 0.0
        if self.type:
            # Due Date #
            today = self._get_default_date()
            if self.type == 'KPB':
                self.due_date = today + relativedelta(days=90)
            elif self.type == 'CLA':
                self.due_date = today + relativedelta(days=60)
            else:
                self.due_date = today
        
    @api.onchange('branch_id')
    def branch_change(self):
        self.supplier_id=self.branch_id.default_supplier_id
    
class wtc_collecting_line(models.Model):
    _name = "wtc.collecting.kpb.line"
    
    collecting_id = fields.Many2one('wtc.collecting.kpb')
    categ = fields.Char('Category')
    kpb_ke = fields.Char('KPB Ke')
    qty = fields.Integer('Qty')
    jasa = fields.Float('Jasa')
    oli = fields.Float('Oli')
    total_jasa = fields.Float('Total Jasa')
    total_oli = fields.Float('Total Oli')