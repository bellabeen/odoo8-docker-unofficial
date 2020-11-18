from openerp import models, fields, api, _
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
import os
import math
from openerp.exceptions import except_orm, Warning, RedirectWarning
import requests
import json
import logging
_logger = logging.getLogger(__name__)


class EpicorConfigPath(models.Model):
    _name = "teds.interface.epicor.config.path"

    name = fields.Char('Path',required=True)
    entity_id = fields.Integer('Entity ID',required=True)

    @api.model
    def create(self,vals):
        src = self.search([('name','!=',False)])
        if src:
            raise Warning('Path sudah dibuat !')
        return super(EpicorConfigPath,self).create(vals)

class InterfaceEpicor(models.Model):
    _name = "teds.interface.epicor"
    _rec_name = "nama_file"

    journal_num = fields.Integer('Journal Num')
    account = fields.Char('Account')
    seq_value_1 = fields.Char('SegValue1')
    seq_value_2 = fields.Char('SegValue2')
    seq_value_3 = fields.Char('SegValue3')
    seq_value_4 = fields.Char('SegValue4')
    seq_value_5 = fields.Char('SegValue5')
    seq_value_6 = fields.Char('SegValue6')
    seq_value_7 = fields.Char('SegValue7')
    seq_value_8 = fields.Char('SegValue8')
    seq_value_9 = fields.Char('SegValue9')
    seq_value_10 = fields.Char('SegValue10')
    seq_value_11 = fields.Char('SegValue11')
    seq_value_12 = fields.Char('SegValue12')
    seq_value_13 = fields.Char('SegValue13')
    seq_value_14 = fields.Char('SegValue14')
    seq_value_15 = fields.Char('SegValue15')
    seq_value_16 = fields.Char('SegValue16')
    seq_value_17 = fields.Char('SegValue17')
    seq_value_18 = fields.Char('SegValue18')
    seq_value_19 = fields.Char('SegValue19',)
    seq_value_20 = fields.Char('SegValue20')
    trans_amt = fields.Float('TransAmt')
    doc_trans_amt = fields.Char('DocTransAmt',default=0)
    curr_acct = fields.Char('CurrAcct',default=0)
    currency_code_acct = fields.Char('CurrencyCodeAcct',default='IDR')
    jedate = fields.Date('JEDate')
    description = fields.Text('Description')
    comment_text = fields.Text('CommentText')
    gl_jedate = fields.Date('GLJrnHedJEDate')
    gl_description = fields.Text('GLJrnHedDescription')
    gl_reverse = fields.Char('GLJrnHedReverse',default=0)
    gl_reverse_date = fields.Date('GLJrnHedReverseDate')
    gl_red_storno = fields.Char('GLJrnHedRedStorno')
    gl_comment_text  = fields.Text('GLJrnHedCommentText')
    bank_c = fields.Char('Bank_c')
    reference_c = fields.Char('Reference_c')
    serial_faktur_pajak_c = fields.Char('SeriFakturPajak_c')
    transaction_type_c = fields.Char('TransactionType_c')
    supplier_c = fields.Char('Supplier_c')
    customer_c = fields.Char('Customer_c')
    invoice_nbr_c = fields.Char('InvoiceNbr_c')
    terms_c = fields.Char('Terms_c')
    item_c = fields.Char('Item_c')
    po_nbr_c = fields.Char('PONbr_c')
    do_nbr_c = fields.Char('DONbr_c')
    id_rec_c = fields.Integer('idRec_c')
    asset_code_c = fields.Char('AssetCode_c')
    number_01 = fields.Char('Number01',default=0)
    number_02 =  fields.Char('Number02',default=0)
    number_03 = fields.Char('Number03',default=0)
    number_04 = fields.Char('Number04',default=0)
    number_05 = fields.Char('Number05',default=0)
    number_06 = fields.Char('Number06',default=0)
    number_07 = fields.Char('Number07',default=0)
    number_08 = fields.Char('Number08',default=0)
    number_09 = fields.Char('Number09',default=0)
    number_10 = fields.Char('Number10',default=0)
    date_01 = fields.Date('Date01')
    date_02 = fields.Date('Date02')
    date_03 = fields.Date('Date03')
    date_04 = fields.Date('Date04')
    date_05 = fields.Date('Date05')
    check_box_01 = fields.Char('CheckBox01')
    check_box_02 = fields.Char('CheckBox02')
    check_box_03 = fields.Char('CheckBox03')
    check_box_04 = fields.Char('CheckBox04')
    check_box_05 = fields.Char('CheckBox05')
    gl_handling = fields.Char('GLJrnHedTaxHandling')
    tax_line = fields.Char('TaxLine')
    tax_liability = fields.Char('TaxLiability')
    tax_type = fields.Char('TaxType')
    tax_rate = fields.Char('TaxRate')
    reporting_module = fields.Char('ReportingModule')
    part_of_dual = fields.Char('PartOfDual')
    tax_point_date = fields.Date('TaxPointDate')
    taxable_line = fields.Char('TaxableLine')
    taxable_amnt_in_tran_curr = fields.Float('TaxableAmntInTranCurr')
    taxable_amnt_in_book_curr = fields.Float('TaxableAmntInBookCurr')
    gl_doc_type = fields.Char('GLJrnHedTranDocType')

    nama_file = fields.Char('Nama File')        
    no_urut = fields.Integer('No Urut')

    _sql_constraints = [('id_rec_c_unique', 'unique(id_rec_c)', 'id_rec_c tidak boleh duplikat.')]
    
    @api.multi
    def action_generate_account_move(self):
        try:
            last_date = """
                SELECT max(jedate) as max_date
                FROM teds_interface_epicor
            """
            self._cr.execute (last_date)
            ress = self._cr.fetchone()
            date_now = datetime.now() + relativedelta(hours=7) - relativedelta(days=1)
            if ress[0]:
                next_date = datetime.strptime(ress[0],'%Y-%m-%d') + relativedelta(days=1)
                selisih = date_now - next_date
                if int(selisih.days) > 0:
                    for x in range(selisih.days):
                        next_date = next_date + relativedelta(days=1)
                        self.generate_account_move(next_date)
                else:
                    self.generate_account_move(date_now)
            else:
                self.generate_account_move(date_now)
        
        except Exception as err:    
            url = "https://hooks.slack.com/services/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"
            headers = {'Content-Type': 'application/json'}
            body = {'text':err}
        
            requests.post(url=url,json=body,headers=headers,verify=True)


    
    @api.multi
    def action_generate_file(self):
        try:
            ceks = """
                SELECT jedate
                FROM teds_interface_epicor
                WHERE nama_file is null
                GROUP by jedate
                ORDER by jedate asc
            """
            self._cr.execute(ceks)
            objs = self.env.cr.fetchall()                
            if len(objs) > 0:
                for obj in objs:
                    self.generate_file(str(obj[0]))
        
        except Exception as err:
            url = "https://hooks.slack.com/services/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"
            headers = {'Content-Type': 'application/json'}
            body = {'text':err}
        
            requests.post(url=url,json=body,headers=headers,verify=True)


    @api.multi
    def generate_account_move(self,date):
        # now = datetime.now() + relativedelta(hours=7) - relativedelta(days=1)
        # date = now.date()
        query_where = " WHERE am.date = '%s' AND (aml.debit+aml.credit) > 0" %(date)

        query = """
                 INSERT INTO teds_interface_epicor 
                    (
                        journal_num
                        , account
                        , seq_value_2
                        , seq_value_8
                        , seq_value_9
                        , seq_value_10
                        , seq_value_11
                        , seq_value_12
                        , seq_value_13
                        , seq_value_14
                        , seq_value_15
                        , seq_value_16
                        , seq_value_17
                        , seq_value_18
                        , seq_value_19
                        , seq_value_20
                        , trans_amt
                        , doc_trans_amt
                        , curr_acct
                        , currency_code_acct
                        , jedate
                        , description
                        , comment_text
                        , gl_jedate
                        , gl_description
                        , gl_comment_text
                        , gl_reverse
                        , gl_reverse_date
                        , gl_red_storno
                        , bank_c
                        , reference_c
                        , serial_faktur_pajak_c
                        , transaction_type_c
                        , supplier_c
                        , customer_c
                        , invoice_nbr_c
                        , terms_c
                        , item_c
                        , po_nbr_c
                        , do_nbr_c
                        , id_rec_c
                        , asset_code_c
                        , number_01
                        , number_02
                        , number_03
                        , number_04
                        , number_05
                        , number_06
                        , number_07
                        , number_08
                        , number_09
                        , number_10
                        , date_01
                        , date_02
                        , date_03
                        , date_04
                        , date_05
                        , check_box_01
                        , check_box_02
                        , check_box_03
                        , check_box_04
                        , check_box_05
                        , gl_handling
                        , tax_line
                        , tax_liability
                        , tax_type
                        , tax_rate
                        , reporting_module
                        , part_of_dual
                        , tax_point_date
                        , taxable_line
                        , taxable_amnt_in_tran_curr
                        , taxable_amnt_in_book_curr
                        , gl_doc_type
                    )
                SELECT 
                    am.id --journal_num--
                    , ac.sap --account--
                    , b.profit_centre --seq_value_2--
                    , CASE WHEN pc2.name = 'AT' THEN '000' --'501' 
                    WHEN pc2.name = 'CUB' THEN  '000' --'502' 
                    WHEN pc2.name = 'SPORT' THEN '000' --'503'
                    ELSE '000' 
                    END --seq_value_8--
                    , NULL --seq_value_9--
                    , NULL --seq_value_10--
                    , NULL --seq_value_11--
                    , NULL --seq_value_12--
                    , NULL --seq_value_13--
                    , NULL --seq_value_14--
                    , NULL --seq_value_15--
                    , NULL --seq_value_16--
                    , NULL --seq_value_17--
                    , NULL --seq_value_18--
                    , NULL --seq_value_19--
                    , NULL --seq_value_20--
                    , (aml.debit-aml.credit) --trans_amt--
                    , 0 --doc_trans_amt--
                    , 0 --curr_acct--
                    , 'IDR' --currency_code_acct--
                    , am.date --jedate--
                    , SUBSTRING(regexp_replace(aml.name, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --description--
                    , SUBSTRING(regexp_replace(am.ref, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --comment_text--
                    , am.date --gl_jedate--
                    , SUBSTRING(regexp_replace(am.name, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --gl_description--
                    , SUBSTRING(regexp_replace(am.ref, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --gl_comment_text--
                    , 0 --gl_reverse--
                    , NULL --gl_reverse_date--
                    , NULL --gl_red_storno--
                    , NULL --bank_c--
                    , SUBSTRING(regexp_replace(am.ref, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --reference_c--
                    , NULL --serial_faktur_pajak_c--
                    , aj.code --transaction_type_c--
                    , NULL --supplier_c--
                    , NULL --customer_c--
                    , SUBSTRING(regexp_replace(am.name, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),1,45) --invoice_nbr_c--
                    , NULL --terms_c--
                    , NULL --item_c--
                    , NULL --po_nbr_c--
                    , NULL --do_nbr_c--
                    , aml.id --id_rec_c--
                    , NULL --asset_code_c-- 
                    , 0 --number_01--
                    , 0 --number_02--
                    , 0 --number_03--
                    , 0 --number_04--
                    , 0 --number_05--
                    , 0 --number_06--
                    , 0 --number_07--
                    , 0 --number_08--
                    , 0 --number_09--
                    , 0 --number_10--
                    , NULL --date_01--
                    , NULL --date_02--
                    , NULL --date_03--
                    , NULL --date_04--
                    , NULL --date_05--
                    , NULL --check_box_01--
                    , NULL --check_box_02--
                    , NULL --check_box_03--
                    , NULL --check_box_04--
                    , NULL --check_box_05--
                    , NULL --gl_handling--
                    , NULL --tax_line--
                    , NULL --tax_liability--
                    , NULL --tax_type--
                    , NULL --tax_rate--
                    , NULL --reporting_module--
                    , NULL --part_of_dual--
                    , NULL --tax_point_date--
                    , NULL --taxble_line--
                    , NULL --taxable_amnt_in_tran_c--
                    , NULL --taxable_amnt_in_book_c--
                    , NULL --gl_doc_type--
                FROM account_move am
                INNER JOIN account_move_line aml ON aml.move_id = am.id
                LEFT JOIN account_account ac ON ac.id = aml.account_id
                LEFT JOIN wtc_branch b ON b.id = aml.branch_id
                LEFT JOIN account_journal aj ON am.journal_id = aj.id
                LEFT JOIN product_product pp ON pp.id = aml.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN product_category pc2 ON pc2.id = pc.parent_id

                %s
                """ %(query_where)
        self._cr.execute(query)
    
    @api.multi
    def generate_file(self,jedate):
        _logger.warning("Date Get %s" %jedate)
        # path = 'D:/epicor/file_epicor/'
        obj_path = self.env['teds.interface.epicor.config.path'].sudo().search([('name','!=',False)],limit=1)
        if not obj_path:
            _logger.warning('Teds Interface Epicore : Path belum di setting') 
            return True
        path = obj_path.name
        # now = datetime.now() + relativedelta(hours=7) - relativedelta(days=1)
        # date = now.date()

        count_id = """
                    SELECT count(distinct journal_num) as count
                    FROM teds_interface_epicor
                    WHERE jedate = '%s' AND nama_file IS NULL
                """ %(jedate)
        self._cr.execute(count_id)
        d = self.env.cr.dictfetchall()                
        n = 1
        tot = int(d[0].get('count',0))
        if tot == 0: # jika tidak ada data, tidak generate file.
            _logger.warning('Teds Interface Epicore : Data tidak ada') 
            return True
        if tot > 300:
            n = int(math.ceil(tot/300)+1)
        for x in range(n):
            ids = []
            group = 'TED'
            urut = False
            company = obj_path.entity_id
            years = jedate[0:4]
            month = jedate[5:7]
            tgl = '{:02}'.format(int(jedate[8:10]))
            jedate = jedate
            journal_code = 'TED'
            journal_desc = 'TED'

            next_urut = """
                        SELECT 
                        COALESCE(MAX (CASE WHEN no_urut IS NOT NULL THEN no_urut END),0) as jml
                        FROM teds_interface_epicor
                        WHERE jedate = '%s'
                    """ %(jedate)
            self._cr.execute(next_urut)
            res = self.env.cr.dictfetchall()
            if res[0].get('jml'):
                a = int(res[0]['jml'])+1
                urut = '{:03}'.format(a)
            else:
                urut = '{:03}'.format(1)

            objs = """
                    SELECT
                    journal_num
                    , account
                    , seq_value_2
                    , COALESCE(seq_value_8,'')
                    , COALESCE(seq_value_9,'')
                    , COALESCE(seq_value_10,'')
                    , COALESCE(seq_value_11,'')
                    , COALESCE(seq_value_12,'')
                    , COALESCE(seq_value_13,'')
                    , COALESCE(seq_value_14,'')
                    , COALESCE(seq_value_15,'')
                    , COALESCE(seq_value_16,'')
                    , COALESCE(seq_value_17,'')
                    , COALESCE(seq_value_18,'')
                    , COALESCE(seq_value_19,'')
                    , COALESCE(seq_value_20,'')
                    , trans_amt
                    , COALESCE(doc_trans_amt,'')
                    , COALESCE(curr_acct,'')
                    , COALESCE(currency_code_acct,'')
                    , to_char(jedate,'MM/DD/YYYY')
                    , regexp_replace(description, E'[\\n\\r,\\'\\"]+', ' ', 'g' )
                    , regexp_replace(comment_text, E'[\\n\\r,\\'\\"]+', ' ', 'g' )
                    , to_char(gl_jedate,'MM/DD/YYYY')
                    , COALESCE(gl_description,'')
                    , COALESCE(gl_reverse,'')
                    , CASE WHEN gl_reverse_date IS NULL THEN '' END
                    , COALESCE(gl_red_storno,'')
                    , COALESCE(regexp_replace(gl_comment_text, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),'')
                    , COALESCE(bank_c,'')
                    , COALESCE(regexp_replace(reference_c, E'[\\n\\r,\\'\\"]+', ' ', 'g' ),'')
                    , COALESCE(serial_faktur_pajak_c,'')
                    , transaction_type_c
                    , COALESCE(supplier_c,'')
                    , COALESCE(customer_c,'')
                    , COALESCE(invoice_nbr_c,'')
                    , COALESCE(terms_c,'')
                    , COALESCE(item_c,'')
                    , COALESCE(po_nbr_c,'')
                    , COALESCE(do_nbr_c,'')
                    , id_rec_c --id_rec_c
                    , COALESCE(asset_code_c,'')
                    , COALESCE(number_01,'')
                    , COALESCE(number_02,'')
                    , COALESCE(number_03,'')
                    , COALESCE(number_04,'')
                    , COALESCE(number_05,'')
                    , COALESCE(number_06,'')
                    , COALESCE(number_07,'')
                    , COALESCE(number_08,'')
                    , COALESCE(number_09,'')
                    , COALESCE(number_10,'')
                    , CASE WHEN date_01 IS NULL THEN '' END
                    , CASE WHEN date_02 IS NULL THEN '' END
                    , CASE WHEN date_03 IS NULL THEN '' END
                    , CASE WHEN date_04 IS NULL THEN '' END
                    , CASE WHEN date_05 IS NULL THEN '' END
                    , COALESCE(check_box_01,'')
                    , COALESCE(check_box_02,'')
                    , COALESCE(check_box_03,'')
                    , COALESCE(check_box_04,'')
                    , COALESCE(check_box_05,'')
                    , COALESCE(gl_handling,'')
                    , COALESCE(tax_line,'')
                    , COALESCE(tax_liability,'')
                    , COALESCE(tax_type,'')
                    , COALESCE(tax_rate,'')
                    , COALESCE(reporting_module,'')
                    , COALESCE(part_of_dual,'')
                    , CASE WHEN tax_point_date IS NULL THEN '' END
                    , COALESCE(taxable_line,'')
                    , CASE WHEN taxable_amnt_in_tran_curr IS NULL THEN '' END
                    , CASE WHEN  taxable_amnt_in_book_curr IS NULL THEN '' END
                    , CASE WHEN  gl_doc_type IS NULL THEN '' END
                    , id
                    FROM teds_interface_epicor
                    WHERE jedate = '%s'
                    AND journal_num IN (
                        SELECT distinct journal_num 
                        FROM teds_interface_epicor 
                        WHERE nama_file IS NULL 
                        ORDER BY journal_num ASC LIMIT 300
                    )
                    ORDER BY journal_num ASC
                """ %(jedate)
            self._cr.execute(objs)
            obj = self.env.cr.fetchall()
            
            file_csv =  str(company)+'_'+str(group)+str(tgl)+'-'+str(urut)+'.csv'        
            file_state = str(company)+'_'+str(group)+str(tgl)+'-'+str(urut)+'_stat.csv'

            content = "JournalNum,SegValue1,SegValue2,SegValue3,SegValue4,SegValue5,SegValue6,SegValue7,SegValue8,SegValue9,SegValue10,SegValue11,SegValue12,SegValue13,SegValue14,SegValue15,SegValue16,SegValue17,SegValue18,SegValue19,SegValue20,TransAmt,DocTransAmt,CurrAcct,CurrencyCodeAcct,JEDate,Description,CommentText,GLJrnHedJEDate,GLJrnHedDescription,GLJrnHedReverse,GLJrnHedReverseDate,GLJrnHedRedStorno,GLJrnHedCommentText,Bank_c,Reference_c,SeriFakturPajak_c,TransactionType_c,Supplier_c,Customer_c,InvoiceNbr_c,Terms_c,Item_c,PONbr_c,DONbr_c,idRec_c,AssetCode_c,Number01,Number02,Number03,Number04,Number05,Number06,Number07,Number08,Number09,Number10,Date01,Date02,Date03,Date04,Date05,CheckBox01,CheckBox02,CheckBox03,CheckBox04,CheckBox05,GLJrnHedTaxHandling,TaxLine,TaxLiability,TaxType,TaxRate,ReportingModule,PartOfDual,TaxPointDate,TaxableLine,TaxableAmntInTranCurr,TaxableAmntInBookCurr,GLJrnHedTranDocType\r\n"
            for me in obj:
                account = str(me[1])
                split = account.split('-')
                account_mapping = ','+split[0]+','+str(me[2])+','
                if len(split) > 1:
                    account_mapping += ','.join(split[1:])+','
                    for x in range(len(split),7):
                        account_mapping += ','
                content += str(me[0])
                content += account_mapping[:-1]+''
                content += ','.join([str(x.encode('ascii','ignore').decode('ascii')) if isinstance(x,unicode) else str(x) for x in me[3:74]])
                content += '\r\n'
                
                # years = me[20][6:10]
                # month = me[20][3:5]
                # day = me[20][0:2]
                # jedate = str(years)+'-'+str(month)+'-'+str(day)
                ids.append(me[74])

            content_stat = "CompanyID,GroupID,FileName,BookID,JEDate,FiscalYear,FiscalPeriod,JournalCode,JournalCodeDescription,Post\r\n"
            
            content_stat += str(company)+','
            content_stat += str(group)
            content_stat += str(tgl)+'-'+str(urut)+','
            content_stat += str(file_csv)+',,'
            content_stat += str(jedate)+','
            content_stat += str(years)+','
            content_stat += str(month)+','
            content_stat += str(journal_code)+','
            content_stat += str(journal_desc)+','+'1'

            csv = open(path+file_csv, 'w+b')
            csv.write(content)
            csv.close()

            stat = open(path+file_state, 'w+b')
            stat.write(content_stat)
            stat.close()

            update_file = """
                UPDATE
                teds_interface_epicor
                set no_urut = '%s'
                , nama_file = '%s'
                WHERE id in %s
            """ %(urut,file_csv,str(tuple(ids)).replace(',)', ')'))
            self._cr.execute(update_file)
