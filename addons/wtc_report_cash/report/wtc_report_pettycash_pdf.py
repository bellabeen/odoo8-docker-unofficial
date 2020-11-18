import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta


class ccc(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(ccc, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
           'no_urut': self.no_urut,
           'test': self._test,
           'account': self._account,
           'sap': self._sap,
           'total_saldo': self._total_saldo,
           'total_credit': self._total_credit,
           'saldo_awal': self._saldo_awal,
           'saldo_akhir_tanggal':self._saldo_akhir_tanggal,
           'looping': self._looping,
           'tgl':self.get_date,
           'usr':self.get_user,
           
        })
        
        self.no = 0

        self.default_account_code=''

    def get_date(self):
        date= self._get_default(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        return date

    def get_user(self):
        user = self._get_default(self.cr, self.uid, user=True).name
        return user

    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
  
    def no_urut(self):
        self.no+=1
        return self.no

    def _test(self,data) :
        journal_id = data['journal_id'][0] if data['journal_id'] else False
        journal_pool = self.pool.get('account.journal').browse(self.cr,self.uid,journal_id)
        default_account = journal_pool.default_debit_account_id or journal_pool.default_credit_account_id
        default_account_code = default_account.code

        return default_account_code

    def _account(self,data) :
        journal_id = data['journal_id'][0] if data['journal_id'] else False
        journal_pool = self.pool.get('account.journal').browse(self.cr,self.uid,journal_id)
        default_account = journal_pool.default_debit_account_id or journal_pool.default_credit_account_id
        default_account_name = default_account.name

        return default_account_name

    def _sap(self,data) :
        journal_id = data['journal_id'][0] if data['journal_id'] else False
        journal_pool = self.pool.get('account.journal').browse(self.cr,self.uid,journal_id)
        default_account = journal_pool.default_debit_account_id or journal_pool.default_credit_account_id
        default_account_sap = default_account.sap

        return default_account_sap

    def _total_saldo(self,data):
        total_saldo=self._lines(data)['total']
        return total_saldo

    def _total_credit(self,data):
        total_credit=self._lines(data)['total_credit']
        return total_credit

    def _saldo_awal(self,data):
        saldo_awal=self._lines(data)['saldo_awal']
        return saldo_awal

    def _saldo_akhir_tanggal(self,data):
        saldo_akhir_tanggal=self._lines(data)['saldo_akhir_tanggal']
        return saldo_akhir_tanggal


    def _looping(self,data):
        loop=self._lines(data)['loop']
        return loop


    def _lines(self, data):
        cr=self.cr
        uid=self.uid

        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']
        journal_id = data['journal_id'][0] if data['journal_id'] else False   
        branch_ids = data['branch_ids']


        tz = '7 hours'
        query_where = " WHERE a.type = 'liquidity' "
        query_saldo_where = ""

        if branch_ids :
            query_where += " AND aml.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if not journal_id :
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('branch_id','in',branch_ids),('type','=','pettycash')])
        if journal_id and isinstance(journal_id, (int, long)) :
            journal_ids = [journal_id]
        if journal_ids :
            journals = self.pool.get('account.journal').browse(cr, uid, journal_ids)
            query_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals if x.type == 'pettycash'])).replace(',)', ')')
            query_saldo_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals if x.type == 'pettycash'])).replace(',)', ')')
        if start_date :
            query_where += " AND aml.date >= '%s' " % start_date
        if end_date :
            query_where += " AND aml.date <= '%s' " % end_date

   

        query_saldo = """
            SELECT SUM(debit - credit) as balance
            FROM account_move_line aml
            WHERE date < '%s'
            %s
            GROUP BY account_id
        """ % (start_date, query_saldo_where)
        cr.execute (query_saldo)
        result = cr.fetchall()
        
        saldo_awal = 0
        if len(result) > 0 and len(result[0]) > 0:
            saldo_awal += result[0][0]
       

        query = """
            SELECT 
            aml.date as date, 
            am.state as state, 
            am.name as move_line_name, 
            p.name as partner_name, 
            aml.name as keterangan, 
            aml.debit as debit, 
            aml.credit as credit, 
            res.name as user_name, 
            to_char(aml.create_date + interval '%s', 'HH12:MI AM') as jam 
            FROM account_move_line aml 
            LEFT JOIN account_move am ON am.id = aml.move_id 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN account_journal aj ON aj.default_debit_account_id = aml.account_id
            LEFT JOIN res_partner p ON p.id = aml.partner_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            LEFT JOIN res_users u ON u.id = aml.create_uid 
            LEFT JOIN res_partner res ON res.id = u.partner_id 
            %s
            ORDER BY aml.id 
            """ % (tz,query_where)


        self.cr.execute(query)
        
        picks = self.cr.fetchall()
       
        ress=[]
        total_debit = 0
        total_credit = 0
        saldo_akhir_tanggal = 0
   
        

        no =1 

        for res in picks :

            # date= self._get_default(cr, uid, date=True, context=context)
            # date = date.strftime("%Y-%m-%d %H:%M:%S").date()
           
            tgl_konf = datetime.strptime(res[0], "%Y-%m-%d").date() if res[0] else ''
            debit = res[5]
            credit = res[6]
            saldo = debit - credit

            total_debit += debit
            total_credit += credit
            saldo_awal = saldo_awal
            
            saldo_akhir_tanggal=saldo_awal+total_debit-total_credit
           

            if no == 1 :
                saldo_awala =saldo
            else :
                saldo_awala += saldo

            no+= 1

            ress.append(

                    {
                    'tgl_konf':tgl_konf,
                    'state':res[1],
                    'move_line_name':res[2],
                    'partner_name':res[3],
                    'keterangan':res[4],
                    'debit':res[5],
                    'credit':res[6],
                    'date':res[0],
                    'user_name':res[7],
                    'jam':res[8],
                    'saldo_awala':saldo,
                    'total_saldo': 0,
                    }
                    
                )

        value={'loop':ress,'total':total_debit, 'total_credit':total_credit, 'saldo_awal':saldo_awal, 'saldo_akhir_tanggal':saldo_akhir_tanggal}
        return value


class report_belajarrr(osv.AbstractModel):
    _name = 'report.wtc_report_cash.wtc_report_pettycash_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_cash.wtc_report_pettycash_pdf'
    _wrapped_report_class = ccc
    
   
