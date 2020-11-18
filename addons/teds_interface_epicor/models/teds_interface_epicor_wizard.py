from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from openerp.exceptions import Warning
import math

class InterfaceEpicorWizard(models.TransientModel):
    _name = "teds.interface.epicor.wizard"
    _rec_name = "date"

    def _get_default_date(self):
        return date.today()

    options = fields.Selection([
        ('generate_file','Generate File'),
        ('clear_file','Clear File')],default='generate_file')
    date = fields.Date('Date',default=_get_default_date)
    jedate = fields.Date('Jedate',default=_get_default_date)
    state_x = fields.Selection([
        ('choose','choose'),
        ('get','get')], default='choose')

    @api.multi
    def generate_file(self):
        if self.options == 'generate_file':
            self.generate_file_csv()
        elif self.options == 'clear_file':
            self.clear_file_name()

        self.write({'state_x':'get'})
        form_id = self.env.ref('teds_interface_epicor.view_teds_interface_epicor_wizard_form').id
        return {
            'name': ('Update'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.interface.epicor.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        } 
    @api.multi
    def clear_file_name(self):
        jedate = self.jedate
        update = """
                    UPDATE teds_interface_epicor
                    SET nama_file = Null
                    WHERE jedate = '%s'
                """ %(jedate)
        self._cr.execute(update)

    @api.multi
    def generate_file_csv(self):
        obj_path = self.env['teds.interface.epicor.config.path'].sudo().search([('name','!=',False)],limit=1)
        if not obj_path:
            raise Warning('Teds Interface Epicore : Path belum di setting') 
        path = obj_path.name
        jedate = self.jedate
        date = self.date
        
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
            raise Warning('Teds Interface Epicore : Data tidak ada') 
        if tot > 300:
            n = int(math.ceil(tot/300)+1)
        for x in range(n):
            ids = []
            group = 'TED'
            urut = False
            company = obj_path.entity_id
            years = jedate[0:4]
            month = jedate[5:7]
            day = jedate[8:10]
            tgl = '{:02}'.format(int(day))
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
                    WHERE journal_num IN (
                        SELECT distinct journal_num 
                        FROM teds_interface_epicor 
                        WHERE nama_file IS NULL 
                        ORDER BY journal_num ASC LIMIT 300)
                    AND jedate = '%s'
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
            content_stat += str(date)+','
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

            self.env['teds.interface.epicor'].browse(ids).write({
                'no_urut':urut,
                'nama_file':file_csv, 
            })


    

