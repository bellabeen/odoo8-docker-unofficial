import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell

class LaporanCashCountWizard(models.TransientModel):
    _name = "teds.laporan.cash.count.wizard"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_datetime(self): 
        return self.env['wtc.branch'].get_default_datetime()

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    date = fields.Date('Tanggal',default=_get_default_date)
    branch_ids = fields.Many2many('wtc.branch', 'teds_cash_count_report_branch_rel', 'cash_count_id', 'branch_id',default=_get_default_branch)

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_font_size(10)
        
        self.wbf['footer'] = workbook.add_format({'align':'left'})
                
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(10)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 

        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        # PUST
        self.wbf['header_pust'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#F0F322','font_color': '#000000'})
        self.wbf['header_pust'].set_border()
        self.wbf['header_pust'].set_font_size(10)

        self.wbf['content_float_pust'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#F0F322'})
        self.wbf['content_float_pust'].set_right() 
        self.wbf['content_float_pust'].set_left()
        
        # PC SR
        self.wbf['header_sr'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#8ACFAC','font_color': '#000000'})
        self.wbf['header_sr'].set_border()
        self.wbf['header_sr'].set_font_size(10)

        self.wbf['content_float_sr'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#8ACFAC'})
        self.wbf['content_float_sr'].set_right() 
        self.wbf['content_float_sr'].set_left()

        self.wbf['content_percent_sr'] = workbook.add_format({'align': 'right','num_format': '0%','bg_color':'#8ACFAC'})
        self.wbf['content_percent_sr'].set_right() 
        self.wbf['content_percent_sr'].set_left() 
        
        # PC WS
        self.wbf['header_ws'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#7CC6D1','font_color': '#000000'})
        self.wbf['header_ws'].set_border()
        self.wbf['header_ws'].set_font_size(10)

        self.wbf['content_float_ws'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#7CC6D1'})
        self.wbf['content_float_ws'].set_right() 
        self.wbf['content_float_ws'].set_left()
 
        self.wbf['content_percent_ws'] = workbook.add_format({'align': 'right','num_format': '0%', 'bg_color':'#7CC6D1'})
        self.wbf['content_percent_ws'].set_right() 
        self.wbf['content_percent_ws'].set_left()
        
        # PC ATL
        self.wbf['header_atl'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FBB87A','font_color': '#000000'})
        self.wbf['header_atl'].set_border()
        self.wbf['header_atl'].set_font_size(10)

        self.wbf['content_float_atl'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#FBB87A'})
        self.wbf['content_float_atl'].set_right() 
        self.wbf['content_float_atl'].set_left()
        
        self.wbf['content_percent_atl'] = workbook.add_format({'align': 'right','num_format': '0%', 'bg_color':'#FBB87A'})
        self.wbf['content_percent_atl'].set_right() 
        self.wbf['content_percent_atl'].set_left()

        # OTHER
        self.wbf['header_other'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#DDDDDD','font_color': '#000000'})
        self.wbf['header_other'].set_border()
        self.wbf['header_other'].set_font_size(10)

        self.wbf['content_other'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#DDDDDD'})
        self.wbf['content_other'].set_right() 
        self.wbf['content_other'].set_left()
    
        # Brankas
        self.wbf['header_brankas'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#2ACDFF','font_color': '#000000'})
        self.wbf['header_brankas'].set_border()
        self.wbf['header_brankas'].set_font_size(10)

        self.wbf['content_brankas'] = workbook.add_format({'align': 'right','num_format': '#,##0.00', 'bg_color':'#2ACDFF'})
        self.wbf['content_brankas'].set_right() 
        self.wbf['content_brankas'].set_left()
        
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
    
        self.wbf['total'] = workbook.add_format({'bg_color': '#FFFFDB'})
        self.wbf['total'].set_right() 
        self.wbf['total'].set_left()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
                
        return workbook

    @api.multi
    def action_export(self):
        self.ensure_one()
        query_where = " WHERE cc.state = 'posted'"

        if self.date:
            query_where += " AND cc.date = '%s'" %(self.date)
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND cc.branch_id in %s" % str(tuple(branch)).replace(',)', ')')

        query = """
            SELECT cash_count.branch_id
            , cash_count.branch_code
            , cash_count.branch_name
            , cash_count.journal
            , COALESCE(plafon_petty_cash_sr,0) as plafon_petty_cash_sr
            , COALESCE(plafon_petty_cash_ws,0) as plafon_petty_cash_ws
            , COALESCE(plafon_petty_cash_atl_btl,0) as plafon_petty_cash_atl_btl
            , COALESCE(fisik_petty_cash_sr,0) as fisik_petty_cash_sr
            , COALESCE(fisik_petty_cash_ws,0) as fisik_petty_cash_ws
            , COALESCE(fisik_petty_cash_atl_btl,0) as fisik_petty_cash_atl_btl
            , COALESCE(saldo_pc_sr,0) as saldo_pc_sr
            , COALESCE(saldo_pc_ws,0) as saldo_pc_ws
            , COALESCE(saldo_pc_atl_btl,0) as saldo_pc_atl_btl
            , COALESCE(cash_sr.amount,0) as cash_sr_amount
            , COALESCE(cash_ws.amount,0) as cash_ws_amount
            , COALESCE(cash_pos_sr.amount,0) as cash_pos_sr_amount
            , COALESCE(cash_pos_ws.amount,0) as cash_pos_ws_amount
            , COALESCE(petty_cash_sr.amount,0) as petty_cash_sr_amount
            , COALESCE(petty_cash_ws.amount,0) as petty_cash_ws_amount
            , COALESCE(petty_cash_pos_sr.amount,0) as petty_cash_pos_sr_amount
            , COALESCE(petty_cash_pos_ws.amount,0) as petty_cash_pos_ws_amount
            , COALESCE(petty_cash_atl.amount,0) as petty_cash_atl_amount
            , COALESCE(reimburse_petty_cash_sr.amount,0) as reimburse_petty_cash_sr_amount
            , COALESCE(reimburse_petty_cash_ws.amount,0) as reimburse_petty_cash_ws_amount
            , COALESCE(reimburse_petty_cash_pos_sr.amount,0) as reimburse_petty_cash_pos_sr_amount
            , COALESCE(reimburse_petty_cash_pos_ws.amount,0) as reimburse_petty_cash_pos_ws_amount
            , COALESCE(reimburse_petty_cash_atl.amount,0) as reimburse_petty_cash_atl_amount
            , COALESCE(penerimaan_lain.amount,0) as penerimaan_lain_amount
            FROM (
                SELECT cc.id
                , b.id as branch_id
                , b.code as branch_code
                , b.name as branch_name
                , cc.plafon_petty_cash_sr
                , cc.plafon_petty_cash_ws
                , cc.plafon_petty_cash_atl_btl
                , cc.fisik_petty_cash_sr
                , cc.fisik_petty_cash_ws
                , cc.fisik_petty_cash_atl_btl
                , cc.saldo_pc_sr
                , cc.saldo_pc_ws
                , cc.saldo_pc_atl_btl
                , journal 
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cc.id = cd.cash_count_id
                INNER JOIN wtc_branch b ON b.id = cc.branch_id
                %(query_where)s
                GROUP BY cd.journal,cc.id,b.id
                ORDER BY journal ASC
            ) cash_count
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                LEFT JOIN teds_cash_count_validasi cv ON cv.id = cd.validasi_id
                %(query_where)s 
                AND cd.type = 'cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%SR%%'
                AND cv.name = 'Belum disetor ke bank'
                GROUP BY cash_count_id,journal
            ) cash_pos_sr ON cash_pos_sr.cash_count_id = cash_count.id AND cash_pos_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                LEFT JOIN teds_cash_count_validasi cv ON cv.id = cd.validasi_id
                %(query_where)s 
                AND cd.type = 'cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%WS%%'
                AND cv.name = 'Belum disetor ke bank'
                GROUP BY cash_count_id,journal
            ) cash_pos_ws ON cash_pos_ws.cash_count_id = cash_count.id AND cash_pos_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                LEFT JOIN teds_cash_count_validasi cv ON cv.id = cd.validasi_id
                %(query_where)s
                AND cd.type = 'cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%SR%%'
                AND cv.name = 'Belum disetor ke bank'
                GROUP BY cash_count_id,journal
            ) cash_sr ON cash_sr.cash_count_id = cash_count.id AND cash_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                LEFT JOIN teds_cash_count_validasi cv ON cv.id = cd.validasi_id
                %(query_where)s 
                AND cd.type = 'cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%WS%%'
                AND cv.name = 'Belum disetor ke bank'
                GROUP BY cash_count_id,journal
            ) cash_ws ON cash_ws.cash_count_id = cash_count.id AND cash_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                %(query_where)s 
                AND cd.type = 'petty_cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%SR%%'
                GROUP BY cash_count_id,journal
            ) petty_cash_sr ON petty_cash_sr.cash_count_id = cash_count.id AND petty_cash_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                %(query_where)s 
                AND cd.type = 'petty_cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%WS%%'
                GROUP BY cash_count_id,journal
            ) petty_cash_ws ON petty_cash_ws.cash_count_id = cash_count.id AND petty_cash_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'petty_cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%SR%%'
                GROUP BY cash_count_id,journal
            ) petty_cash_pos_sr ON petty_cash_pos_sr.cash_count_id = cash_count.id AND petty_cash_pos_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                %(query_where)s 
                AND cd.type = 'petty_cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%WS%%'
                GROUP BY cash_count_id,journal
            ) petty_cash_pos_ws ON petty_cash_pos_ws.cash_count_id = cash_count.id AND petty_cash_pos_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'petty_cash'
                AND journal ilike '%%ATLBTL%%'
                GROUP BY cash_count_id,journal
            ) petty_cash_atl ON petty_cash_atl.cash_count_id = cash_count.id AND petty_cash_atl.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'reimburse_petty_cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%SR%%'
                GROUP BY cash_count_id,journal
            ) reimburse_petty_cash_sr ON reimburse_petty_cash_sr.cash_count_id = cash_count.id AND reimburse_petty_cash_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'reimburse_petty_cash'
                AND journal not ilike '%%POS%%' AND journal ilike '%%WS%%'
                GROUP BY cash_count_id,journal
            ) reimburse_petty_cash_ws ON reimburse_petty_cash_ws.cash_count_id = cash_count.id AND reimburse_petty_cash_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'reimburse_petty_cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%SR%%'
                GROUP BY cash_count_id,journal
            ) reimburse_petty_cash_pos_sr ON reimburse_petty_cash_pos_sr.cash_count_id = cash_count.id AND reimburse_petty_cash_pos_sr.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id
                %(query_where)s 
                AND cd.type = 'reimburse_petty_cash'
                AND journal ilike '%%POS%%' AND journal ilike '%%WS%%'
                GROUP BY cash_count_id,journal
            ) reimburse_petty_cash_pos_ws ON reimburse_petty_cash_pos_ws.cash_count_id = cash_count.id AND reimburse_petty_cash_pos_ws.journal = cash_count.journal
            LEFT JOIN (
                SELECT cash_count_id
                , journal
                , SUM(amount) as amount
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_detail cd ON cd.cash_count_id = cc.id 
                %(query_where)s 
                AND cd.type = 'reimburse_petty_cash'
                AND journal ilike '%%ATLBTL%%'
                GROUP BY cash_count_id,journal
            ) reimburse_petty_cash_atl ON reimburse_petty_cash_atl.cash_count_id = cash_count.id AND reimburse_petty_cash_atl.journal = cash_count.journal
            LEFT JOIN (
                SELECT COALESCE(sum(amount),0) as amount
                , cc.id as cash_count_id
                FROM teds_cash_count cc
                INNER JOIN teds_cash_count_other co ON co.cash_count_id = cc.id
                WHERE cc.state = 'posted' 
                GROUP BY cc.id
            ) penerimaan_lain ON penerimaan_lain.cash_count_id = cash_count.id
        ORDER BY branch_code,journal ASC    
        """ %{'query_where':query_where}
        self._cr.execute (query)
        ress =  self._cr.dictfetchall()

        result = {}
        for res in ress:
            branch_code = res.get('branch_code')
            branch_name = res.get('branch_name')
            journal = res.get('journal')
            plafon_petty_cash_sr = res.get('plafon_petty_cash_sr')
            plafon_petty_cash_ws = res.get('plafon_petty_cash_ws')
            plafon_petty_cash_atl_btl = res.get('plafon_petty_cash_atl_btl')
            fisik_petty_cash_sr = res.get('fisik_petty_cash_sr')
            fisik_petty_cash_ws = res.get('fisik_petty_cash_ws')
            fisik_petty_cash_atl_btl = res.get('fisik_petty_cash_atl_btl')
            saldo_pc_sr = res.get('saldo_pc_sr')
            saldo_pc_ws = res.get('saldo_pc_ws')
            saldo_pc_atl_btl = res.get('saldo_pc_atl_btl')
            cash_sr_amount = res.get('cash_sr_amount')
            cash_ws_amount = res.get('cash_ws_amount')
            cash_pos_sr_amount = res.get('cash_pos_sr_amount')
            cash_pos_ws_amount = res.get('cash_pos_ws_amount')
            petty_cash_sr_amount = res.get('petty_cash_sr_amount')
            petty_cash_ws_amount = res.get('petty_cash_ws_amount')
            petty_cash_pos_sr_amount = res.get('petty_cash_pos_sr_amount')
            petty_cash_pos_ws_amount = res.get('petty_cash_pos_ws_amount')
            petty_cash_atl_amount = res.get('petty_cash_atl_amount')
            reimburse_petty_cash_sr_amount = res.get('reimburse_petty_cash_sr_amount')
            reimburse_petty_cash_ws_amount = res.get('reimburse_petty_cash_ws_amount')
            reimburse_petty_cash_pos_sr_amount = res.get('reimburse_petty_cash_pos_sr_amount')
            reimburse_petty_cash_pos_ws_amount = res.get('reimburse_petty_cash_pos_ws_amount')
            reimburse_petty_cash_atl_amount = res.get('reimburse_petty_cash_atl_amount')
            penerimaan_lain_amount = res.get('penerimaan_lain_amount')

            # Untuk identifikasi POS atau bukan default nama cabang
            branch_type = branch_name
            if 'POS' in journal:
                branch_type = "%s - POS" %branch_name

            # KEY RESULT 
            cabang_jurnal = "%s|%s" %(branch_code,branch_type)
            if not result.get(cabang_jurnal):
                result[cabang_jurnal] = {
                    'branch_code':branch_code,
                    'branch_name':branch_type,

                    # PUST
                    'pust_sr':cash_pos_sr_amount if 'POS' in journal else cash_sr_amount,
                    'pust_ws':cash_pos_ws_amount if 'POS' in journal else cash_ws_amount ,

                    # PETTY CASH SR
                    'pc_sr_plafon':plafon_petty_cash_sr if 'POS' not in journal else 0,
                    'pc_sr_saldo_fisik':fisik_petty_cash_sr if 'POS' not in journal else 0,
                    'pc_sr_saldo_bank_out':saldo_pc_sr if 'POS' not in journal else 0,
                    'pc_sr_saldo_reimburse':reimburse_petty_cash_sr_amount,
                    'pc_sr_outstanding':petty_cash_sr_amount,

                    # PETTY CASH WS
                    'pc_ws_plafon':plafon_petty_cash_ws if 'POS' not in journal else 0,
                    'pc_ws_saldo_fisik':fisik_petty_cash_ws if 'POS' not in journal else 0,
                    'pc_ws_saldo_bank_out':saldo_pc_ws if 'POS' not in journal else 0,
                    'pc_ws_saldo_reimburse':reimburse_petty_cash_ws_amount,
                    'pc_ws_outstanding':petty_cash_ws_amount,

                    # PETTY CASH ATL/BTL
                    'pc_atl_plafon':plafon_petty_cash_atl_btl if 'POS' not in journal else 0,
                    'pc_atl_saldo_fisik':fisik_petty_cash_atl_btl if 'POS' not in journal else 0,
                    'pc_atl_saldo_bank_out':saldo_pc_atl_btl if 'POS' not in journal else 0,
                    'pc_atl_saldo_reimburse':reimburse_petty_cash_atl_amount,
                    'pc_atl_outstanding':petty_cash_atl_amount,

                    # Penerimaan Lain
                    'saldo_penerimaan_lain':penerimaan_lain_amount,
                }
            else:
                # PUST
                result[cabang_jurnal]['pust_sr'] += cash_pos_sr_amount if 'POS' in journal else cash_sr_amount
                result[cabang_jurnal]['pust_ws'] += cash_pos_ws_amount if 'POS' in journal else cash_ws_amount
                
                # PETTY CASH SR
                result[cabang_jurnal]['pc_sr_saldo_reimburse'] += reimburse_petty_cash_sr_amount
                result[cabang_jurnal]['pc_sr_outstanding'] += petty_cash_sr_amount

                # PETTY CASH WS
                result[cabang_jurnal]['pc_ws_saldo_reimburse'] += reimburse_petty_cash_ws_amount
                result[cabang_jurnal]['pc_ws_outstanding'] += petty_cash_ws_amount

                # PETTY CASH ATL/BTL
                result[cabang_jurnal]['pc_atl_saldo_reimburse'] += reimburse_petty_cash_atl_amount
                result[cabang_jurnal]['pc_atl_outstanding'] += petty_cash_atl_amount

        # Excel
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Cash Count')
        worksheet.set_column('A1:A1',14)
        worksheet.set_column('B1:B1',23)
        worksheet.set_column('C1:C1',17)
        worksheet.set_column('D1:D1',17)
        worksheet.set_column('E1:E1',18)
        worksheet.set_column('F1:F1',25)
        worksheet.set_column('G1:G1',28)
        worksheet.set_column('H1:H1',18)
        worksheet.set_column('I1:I1',25)
        worksheet.set_column('J1:J1',22)
        worksheet.set_column('K1:K1',22)
        worksheet.set_column('L1:L1',22)
        worksheet.set_column('M1:M1',22)
        worksheet.set_column('N1:N1',22)
        worksheet.set_column('O1:O1',22)
        worksheet.set_column('P1:P1',22)
        worksheet.set_column('Q1:Q1',22)
        worksheet.set_column('R1:R1',22)
        worksheet.set_column('S1:S1',22)
        worksheet.set_column('T1:T1',22)
        worksheet.set_column('U1:U1',22)
        worksheet.set_column('V1:V1',22)
        worksheet.set_column('W1:W1',22)
        worksheet.set_column('X1:X1',22)

        date = self._get_default_datetime()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Cash Count %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Cash Count', wbf['company'])
        worksheet.merge_range('A2:C2', 'Tanggal %s' %self.date, wbf['company'])

        worksheet.merge_range('A4:A5', 'Kode Cabang', wbf['header'])
        worksheet.merge_range('B4:B5', 'Nama Cabang', wbf['header'])
        worksheet.merge_range('C4:D4', 'PUST', wbf['header_pust'])
        worksheet.write('C5', 'Showroom', wbf['header_pust'])
        worksheet.write('D5', 'Workshop', wbf['header_pust'])
        worksheet.merge_range('E4:J4', 'Petty Cash SR', wbf['header_sr'])
        worksheet.write('E5', 'Plafon', wbf['header_sr'])
        worksheet.write('F5', 'Saldo Fisik', wbf['header_sr'])
        worksheet.write('G5', 'Saldo di Bank Out', wbf['header_sr'])
        worksheet.write('H5', 'Saldo Reimburse', wbf['header_sr'])
        worksheet.write('I5', 'PC Outstanding', wbf['header_sr'])
        worksheet.write('J5', 'Pemakaian (%)', wbf['header_sr'])
        worksheet.merge_range('K4:P4', 'Petty Cash WS', wbf['header_ws'])
        worksheet.write('K5', 'Plafon', wbf['header_ws'])
        worksheet.write('L5', 'Saldo Fisik', wbf['header_ws'])
        worksheet.write('M5', 'Saldo di Bank Out', wbf['header_ws'])
        worksheet.write('N5', 'Saldo Reimburse', wbf['header_ws'])
        worksheet.write('O5', 'PC Outstanding', wbf['header_ws'])
        worksheet.write('P5', 'Pemakaian (%)', wbf['header_ws'])
        worksheet.merge_range('Q4:V4', 'Petty Cash ATLBTL', wbf['header_atl'])
        worksheet.write('Q5', 'Plafon', wbf['header_atl'])
        worksheet.write('R5', 'Saldo Fisik', wbf['header_atl'])
        worksheet.write('S5', 'Saldo di Bank Out', wbf['header_atl'])
        worksheet.write('T5', 'Saldo Reimburse', wbf['header_atl'])
        worksheet.write('U5', 'PC Outstanding', wbf['header_atl'])
        worksheet.write('V5', 'Pemakaian (%)', wbf['header_atl'])
        worksheet.merge_range('W4:W5', 'Penerimaan Lain', wbf['header_other'])
        worksheet.merge_range('X4:X5', 'Saldo Brankas', wbf['header_brankas'])
        
        row=6
        row1 = row
        for r in result.values():
            # PUST
            pust_sr = r.get('pust_sr')
            pust_ws = r.get('pust_ws')
            # SR
            pc_sr_plafon = r.get('pc_sr_plafon')
            pc_sr_saldo_fisik = r.get('pc_sr_saldo_fisik')
            pc_sr_saldo_reimburse = r.get('pc_sr_saldo_reimburse')
            pc_sr_outstanding = r.get('pc_sr_outstanding')
            pc_sr_pemakaian = 0
            if pc_sr_plafon > 0:
                pc_sr_pemakaian = (pc_sr_saldo_reimburse + pc_sr_outstanding) / pc_sr_plafon
            
            # WS
            pc_ws_plafon = r.get('pc_ws_plafon')
            pc_ws_saldo_fisik = r.get('pc_ws_saldo_fisik')
            pc_ws_saldo_reimburse = r.get('pc_ws_saldo_reimburse')
            pc_ws_outstanding = r.get('pc_ws_outstanding')
            pc_ws_pemakaian = 0
            if pc_ws_plafon > 0:
                pc_ws_pemakaian = (pc_ws_saldo_reimburse + pc_ws_outstanding) / pc_ws_plafon
            
            # ATL/BTL
            pc_atl_plafon = r.get('pc_atl_plafon')
            pc_atl_saldo_fisik = r.get('pc_atl_saldo_fisik')
            pc_atl_saldo_reimburse = r.get('pc_atl_saldo_reimburse')
            pc_atl_outstanding = r.get('pc_atl_outstanding')
            pc_atl_pemakaian = 0
            if pc_atl_plafon > 0:
                pc_atl_pemakaian = (pc_atl_saldo_reimburse + pc_atl_outstanding) / pc_atl_plafon

            # PENERIMAAN LAIN
            saldo_penerimaan_lain = r.get('saldo_penerimaan_lain')

            saldo_brankas = pust_sr + pust_ws + pc_sr_saldo_fisik + pc_ws_saldo_fisik + pc_atl_saldo_fisik + saldo_penerimaan_lain

            worksheet.write('A%s' % row, r.get('branch_code') , wbf['content'])  
            worksheet.write('B%s' % row, r.get('branch_name') , wbf['content'])                    
            # PUST
            worksheet.write('C%s' % row, pust_sr , wbf['content_float_pust'])
            worksheet.write('D%s' % row, pust_ws , wbf['content_float_pust'])

            # PETTY CASH SR
            worksheet.write('E%s' % row, pc_sr_plafon , wbf['content_float_sr'])
            worksheet.write('F%s' % row, pc_sr_saldo_fisik , wbf['content_float_sr'])
            worksheet.write('G%s' % row, r.get('pc_sr_saldo_bank_out') , wbf['content_float_sr'])
            worksheet.write('H%s' % row, pc_sr_saldo_reimburse, wbf['content_float_sr'])
            worksheet.write('I%s' % row, pc_sr_outstanding , wbf['content_float_sr'])
            worksheet.write('J%s' % row, pc_sr_pemakaian , wbf['content_percent_sr'])
            
            # PETTY CASH WS
            worksheet.write('K%s' % row, pc_ws_plafon , wbf['content_float_ws'])
            worksheet.write('L%s' % row, pc_ws_saldo_fisik , wbf['content_float_ws'])
            worksheet.write('M%s' % row, r.get('pc_ws_saldo_bank_out') , wbf['content_float_ws'])
            worksheet.write('N%s' % row, pc_ws_saldo_reimburse, wbf['content_float_ws'])
            worksheet.write('O%s' % row, pc_ws_outstanding , wbf['content_float_ws'])
            worksheet.write('P%s' % row, pc_ws_pemakaian , wbf['content_percent_ws'])
            
            # PETTY CASH ATL/BTL
            worksheet.write('Q%s' % row, pc_atl_plafon , wbf['content_float_atl'])
            worksheet.write('R%s' % row, pc_atl_saldo_fisik , wbf['content_float_atl'])
            worksheet.write('S%s' % row, r.get('pc_atl_saldo_bank_out') , wbf['content_float_atl'])
            worksheet.write('T%s' % row, pc_atl_saldo_reimburse, wbf['content_float_atl'])
            worksheet.write('U%s' % row, pc_atl_outstanding , wbf['content_float_atl'])
            worksheet.write('V%s' % row, pc_atl_pemakaian , wbf['content_percent_atl'])
            
            worksheet.write('W%s' % row, saldo_penerimaan_lain , wbf['content_other'])
            worksheet.write('X%s' % row, saldo_brankas , wbf['content_brankas'])
            
            row += 1

        worksheet.merge_range('A%s:X%s' % (row,row), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_cash_count.view_teds_laporan_cash_count_wizard').id

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.cash.count.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }