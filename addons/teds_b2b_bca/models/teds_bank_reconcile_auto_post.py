from openerp import api, fields, models
from openerp.exceptions import Warning

class TedsBankMutasi(models.Model):
    _inherit = "teds.bank.mutasi"

    @api.multi
    def schedule_auto_posting_bca(self):
        query = """
            SELECT trim(remark) as remark
            , bm.name as no_rk
            , bm.id as rk_id
            , bm. no_sistem
            , bm.amount
            , bm.branch_id
            , aj.id as journal_id
            , aj.code as journal_code
            , aa.id as account_id
            , (select id from account_journal where code = 'BK01HHO') as payment_to_id
            , (select id from account_journal where code = 'BK05MML') as payment_to_mml_id
            , (select id from res_partner where default_code = 'BCA') as partner_id
            , (select id from account_account where code = '812102') as account_biaya_admin_id
            , (select id from account_account where code = '711102') as account_bunga_id
            , COALESCE(aj.company_id,b.company_id) as company_id
            , COALESCE(aj.currency,c.currency_id) as currency_id
            FROM teds_bank_mutasi bm
            INNER JOIN wtc_branch b ON b.id = bm.branch_id
            INNER JOIN account_account aa ON aa.id = bm.account_id
            INNER JOIN account_journal aj ON aj.default_debit_account_id = aa.id
            LEFT JOIN res_company c ON c.id = aj.company_id
            WHERE  bm.name IS NOT NULL
            AND bm.state = 'Outstanding'
            AND bm.is_posted = True
            AND (bm.no_sistem IS NULL or bm.no_sistem = '')
            AND bm.format = 'bca'
            ORDER BY remark ASC
            LIMIT 10
        """
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        for res in ress:
            remark = res.get('remark')
            branch_id = res.get('branch_id')
            journal_id = res.get('journal_id')
            journal_code = res.get('journal_code')
            amount = res.get('amount')
            rk_id = res.get('rk_id')
            partner_id = res.get('partner_id')
            payment_to_id = res.get('payment_to_id')
            payment_to_mml_id = res.get('payment_to_mml_id')
            account_id = res.get('account_id')
            account_biaya_admin_id = res.get('account_biaya_admin_id')
            account_bunga_id = res.get('account_bunga_id')
            company_id = res.get('company_id')
            currency_id = res.get('currency_id')
            me = self.browse(rk_id)

            if (remark[0:17] == 'TRSF E-BANKING DB') and (remark[-23:] == 'KE PS TUNAS DWIPA MATRA'):
                branch_destination_id = 'HHO'
                # Kusus untuk DLR ke MML PAYMENT TO ID NYA
                if journal_code == 'BK01DLR':
                    branch_destination_id = 'MML'
                    payment_to_id = payment_to_mml_id

                vals = {
                    'branch_id':branch_id,
                    'division':'Unit',
                    'payment_from_id':journal_id,
                    'description': remark,
                    'amount':amount,
                    'amount_show':amount,
                    'line_ids':[[0,False,{
                        'branch_destination_id':branch_destination_id,
                        'payment_to_id':payment_to_id,
                        'description':remark,
                        'amount':amount
                    }]]
                }
                create_bank_transfer = self.env['wtc.bank.transfer'].create(vals)
                create_bank_transfer.signal_workflow('approval_request')
                create_bank_transfer.signal_workflow('approval_approve')
                create_bank_transfer.signal_workflow('banktranster_post')
                me.no_sistem = create_bank_transfer.name
                # raise Warning("Create Bank Transfer Success %s!"%create_bank_transfer.name)
            elif remark == 'BIAYA ADM':
                vals = {
                    'branch_id':branch_id,
                    'division':'Unit',
                    'inter_branch_id':branch_id,
                    'partner_type':'customer',
                    'partner_id':partner_id,
                    'amount':amount,
                    'journal_id':journal_id,
                    'name':remark,
                    'company_id':company_id,
                    'currency_id':currency_id,
                    'account_id':account_id,
                    'type':'payment',
                    'line_wo_ids':[[0,False,{
                        'account_id':account_biaya_admin_id,
                        'name':remark,
                        'type':'wo',
                        'amount':amount,
                    }]]
                }
                create_pv_biaya_admin = self.env['wtc.account.voucher'].create(vals)
                create_pv_biaya_admin.request_approval()
                create_pv_biaya_admin.approval_approve()
                create_pv_biaya_admin.proforma_voucher()
                me.no_sistem = create_pv_biaya_admin.number
            
            elif remark == 'PAJAK BUNGA':
                vals = {
                    'branch_id':branch_id,
                    'division':'Unit',
                    'inter_branch_id':branch_id,
                    'partner_type':'customer',
                    'partner_id':partner_id,
                    'amount':amount,
                    'journal_id':journal_id,
                    'name':remark,
                    'company_id':company_id,
                    'currency_id':currency_id,
                    'account_id':account_id,
                    'type':'payment',
                    'line_wo_ids':[[0,False,{
                        'account_id':account_bunga_id,
                        'name':remark,
                        'type':'wo',
                        'amount':amount,
                    }]]
                }
                create_pv_biaya_admin = self.env['wtc.account.voucher'].create(vals)
                create_pv_biaya_admin.request_approval()
                create_pv_biaya_admin.approval_approve()
                create_pv_biaya_admin.proforma_voucher()
                me.no_sistem = create_pv_biaya_admin.number
            elif remark == 'BUNGA':
                vals = {
                    'branch_id':branch_id,
                    'division':'Unit',
                    'inter_branch_id':branch_id,
                    'partner_type':'customer',
                    'partner_id':partner_id,
                    'amount':amount,
                    'journal_id':journal_id,
                    'name':remark,
                    'company_id':company_id,
                    'currency_id':currency_id,
                    'account_id':account_id,
                    'type':'receipt',
                    'line_wo_ids':[[0,False,{
                        'account_id':account_bunga_id,
                        'name':remark,
                        'type':'wo',
                        'amount':amount,
                    }]]
                }
                create_ar_bunga = self.env['wtc.account.voucher'].create(vals)
                create_ar_bunga.validate_or_rfa()
                me.no_sistem = create_ar_bunga.number
        self.button_reconcile()
