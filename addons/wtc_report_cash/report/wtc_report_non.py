import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from openerp.sql_db import db_connect
from openerp.tools.config import config

class bbb(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(bbb, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
           'no_urut': self.no_urut,
           'looping': self._looping,
           'total_tunai': self._total_tunai,
           'total_total': self._total_total,
           'total_saldo': self._total_saldo,
           'total_bank_and_checks': self._total_bank_and_checks,
           'tgl':self.get_date,
           'usr':self.get_user,
       
           
        })
        
        self.no = 0
  
    def no_urut(self):
        self.no+=1
        return self.no

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

    def _total_bank_and_checks(self,data):
        total_bank_and_checks=self._lines(data)['total_bank_and_checks']
        return total_bank_and_checks


    def _total_saldo(self,data):
        total_saldo=self._lines(data)['total_saldo']
        return total_saldo

    def _total_tunai(self,data):
        total_tunai=self._lines(data)['total_tunai']
        return total_tunai


    def _total_total(self,data):
        total_total=self._lines(data)['total']
        return total_total

    def _looping(self,data):
        loop=self._lines(data)['loop']
        return loop

    
    def _lines(self, data):
        cr=self.cr
        uid=self.uid

        option = data['option']  
        branch_ids = data['branch_ids']
        journal_ids = data['journal_ids']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
                 
        tz = '7 hours'
        journal_type = ['bank','cash','edc']
        query_where = " WHERE 1=1  "

        if option == 'Cash' :
            journal_type = ['cash']
            #query_where += " AND a.type = 'liquidity' "
        elif option == 'EDC' :
            journal_type = ['edc']
            #query_where += " AND a.type = 'receivable' "
        elif option == 'Bank' :
            journal_type = ['bank']
            #query_where += " AND a.type = 'liquidity' "  
        elif option == 'Petty Cash' :
            journal_type = ['pettycash']
            #query_where += " AND a.type = 'liquidity' "
        
        if branch_ids :
            query_where += " AND aml.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')')             
            
        if not journal_ids :
            journal_ids = self.pool.get('account.journal').search(self.cr, self.uid, [('branch_id','in',branch_ids),('type','in',journal_type)])
        if journal_ids :
            journals = self.pool.get('account.journal').browse(self.cr, self.uid, journal_ids)
            query_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals])).replace(',)', ')')
                          
        query_where_saldo = query_where

        if status == 'outstanding' :
            query_where += " AND aml.reconcile_id is Null "
        elif status == 'reconcile' :
            query_where += " AND aml.reconcile_id is not Null "   
                        
        if start_date :
            query_where_saldo += " AND aml.date < '%s' " % start_date
            query_where += " AND aml.date >= '%s' " % start_date
        if end_date :
            query_where += " AND aml.date <= '%s' " % end_date

        query_saldo_awal = """
            (SELECT
            '%s' as tanggal
            , b.code as branch_code
            , '11:59 PM' as Jam
            , '' as kwitansi_name
            , a.code as account_code
            , 'Saldo Awal ' || a.code as keterangan
            , sum(aml.debit - aml.credit) as balance
            , 'saldo_awal' as journal_type
            , '' as scr
            , 0 as id
            FROM account_move_line aml 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            %s
            GROUP BY b.code, a.code
            ORDER BY a.code, b.code)
            """ % (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1), query_where_saldo)

                                                     
        query_trx = """
            (SELECT 
            aml.date as tanggal, 
            b.code as branch_code, 
            to_char(am.create_date + interval '%s', 'HH12:MI AM') as jam, 
            k.name as kwitansi_name, 
            a.code as account_code, 
            aml.name as keterangan, 
            aml.debit - aml.credit as balance, 
            j.type as journal_type, 
            am.name as scr 
            , aml.id as id
            FROM account_move_line aml 
            LEFT JOIN account_move am ON am.id = aml.move_id 
            LEFT JOIN account_journal j ON j.id = aml.journal_id 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN wtc_register_kwitansi_line k ON k.id = aml.kwitansi_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            %s
            ORDER BY a.code, b.code, aml.id)
            """ % (tz,query_where)  

        query = """
            SELECT * 
            FROM (%s UNION %s) a
            ORDER BY branch_code, id
            """ % (query_saldo_awal, query_trx)

        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        # self.cr.execute(query)
 
        # picks = self.cr.fetchall()
        cur.execute(query)
        picks = cur.fetchall()
        cur.close()
       
        ress=[]
        total_tunai = 0
        total_saldo=0
        total_total=0
        total_bank_and_checks = 0
        no =1 

        
        tot_seblum=0
        for res in picks :
            saldo_awal = res[6] if res[7] == 'saldo_awal' else 0.0
            tunai= res[6] if res[7] == 'cash' else 0.0 
            bank_check= res[6] if res[7] == 'bank' else 0.0 

            total= res[6]
            total_total = total
           


            if no == 1 :
                total=res[6] #balance
                tot_seblum+=res[6] #balance
            else :
                # total = res[6]
                total=tot_seblum+res[6]
                tot_seblum=total

            no+= 1


            
            total_saldo += res[6] if res[7] == 'saldo_awal' else 0.0
            total_bank_and_checks += bank_check
            total_tunai += tunai
            total_total = total_saldo + total_tunai + total_bank_and_checks

       

            
            ress.append(

                    {
                    'branch_code':res[1],
                    'tanggal':res[0],
                    'jam':res[2],
                    'kwitansi_name':res[3],
                    'account_code':res[4],
                    'keterangan':res[5],
                    'saldo_awal':saldo_awal,
                    'tunai':tunai,
                    'total':total,
                    'bank_check':bank_check,

                    }

                )
       
       
        value={'loop':ress,'total_tunai':total_tunai, 'total': total_total, 'total_saldo': total_saldo, 'total_bank_and_checks': total_bank_and_checks}
        return  value



            
class report_belajar(osv.AbstractModel):
    _name = 'report.wtc_report_cash.wtc_report_non'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_cash.wtc_report_non'
    _wrapped_report_class = bbb
    
   