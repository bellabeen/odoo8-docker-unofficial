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
import calendar

class LaporanStockOpnameWizard(models.TransientModel):
    _name = "teds.laporan.stock.opname.wizard"

    wbf = {}

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False

    def _get_default_tahun(self):
        return datetime.today().date().year
    
    name = fields.Char('Filename')
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([
        ('STNK','STNK'),
        ('BPKB','BPKB'),
        ('Direct Gift','Direct Gift'),
        ('Unit','Unit'),
        ('Asset','Asset')],string='Options')
    status = fields.Selection([
        ('ALL','ALL'),
        ('Outstanding','Outstanding'),
        ('Done','Done')],default='Outstanding')
    periode = fields.Selection([('01','Januari'),
        ('02','Februari'),
        ('03','Maret'),
        ('04','April'),
        ('05','Mei'),
        ('06','Juni'),
        ('07','Juli'),
        ('08','Agustus'),
        ('09','September'),
        ('10','Oktober'),
        ('11','November'),
        ('12','Desember')], 'Periode')
    tahun = fields.Char('Tahun',default=_get_default_tahun)
    branch_ids = fields.Many2many('wtc.branch', 'teds_stock_opname_report_branch_rel', 'report_id','branch_id', string='Dealer',default=_get_default_branch)
    
    @api.multi
    def add_workbook_format(self, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_number'] = workbook.add_format({'align': 'center'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
        
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook
    
    # Laporan SO
    @api.multi
    def excel_report(self):
        if self.options == 'STNK':
            return self.laporan_so_stnk()
        elif self.options == 'BPKB':
            return self.laporan_so_bpkb()
        elif self.options == 'Direct Gift':
            return self.laporan_so_dg()
        elif self.options == 'Unit':
            return self.laporan_so_unit()
        elif self.options == 'Asset':
            return self.laporan_so_asset()
        else:
            raise Warning("Options tidak dikenal !")

    def laporan_so_dg(self):
        return True

    def laporan_so_unit(self):
        return True

    def laporan_so_stnk(self):
        query_where = " WHERE 1=1"
        if self.status == 'Outstanding':
            query_where += " AND sot.state = 'draft'"
        if self.status == 'Done':
            query_where += " AND sot.state = 'posted'"
        if self.branch_ids:
            branch_ids = [b.id for b in self.branch_ids]   
            query_where +=" AND sot.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if self.periode and self.tahun:
            query_where +=" AND to_char(sot.date,'MM') = '%s' AND to_char(sot.date,'YYYY') = '%s'" %(self.periode,self.tahun)

            
        query = """
            SELECT 
            b.code as code
            , b.name as branch
            , sot.name as no_so
            , sot.staff_bbn
            , sot.adh
            , sot.soh
            , sot.date as tgl_so
            , sot.division
            , sot.generate_date
            , cp.name as create_by
            , sot.create_date as create_on
            , posp.name as post_by
            , sot.post_date as post_on
            , sot.state
            FROM teds_stock_opname_stnk sot
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN res_users c ON c.id = sot.create_uid
            INNER JOIN res_partner cp ON cp.id = c.partner_id 
            LEFT JOIN res_users pos ON pos.id = sot.post_uid
            LEFT JOIN res_partner posp ON posp.id = pos.partner_id 
            %s
        """ % (query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('STNK')
        worksheet.set_column('B1:B1',6)
        worksheet.set_column('C1:C1',22)
        worksheet.set_column('D1:D1',22)
        worksheet.set_column('E1:E1',13)
        worksheet.set_column('F1:F1',13)
        worksheet.set_column('G1:G1',24)
        worksheet.set_column('H1:H1',24)
        worksheet.set_column('I1:I1',24)
        worksheet.set_column('J1:J1',24)
        worksheet.set_column('K1:K1',24)
        worksheet.set_column('L1:L1',12)
        worksheet.set_column('M1:M1',24)
        worksheet.set_column('N1:N1',24)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname STNK %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Stock Opname STNK', wbf['company'])
        worksheet.merge_range('A2:C2', 'Periode %s %s'%(calendar.month_name[int(self.periode)],self.tahun), wbf['company'])
        worksheet.merge_range('A3:C3', 'Status %s'%(self.status), wbf['company'])

        row=4
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'Code', wbf['header_no'])
        worksheet.write('C%s' %(row+1), 'Cabang', wbf['header_no'])
        worksheet.write('D%s' %(row+1), 'No SO', wbf['header_no'])
        worksheet.write('E%s' %(row+1), 'Tgl SO', wbf['header_no'])
        worksheet.write('F%s' %(row+1), 'Division', wbf['header_no'])
        worksheet.write('G%s' %(row+1), 'Staff BBN', wbf['header_no'])
        worksheet.write('H%s' %(row+1), 'ADH', wbf['header_no'])
        worksheet.write('I%s' %(row+1), 'SOH', wbf['header_no'])
        worksheet.write('J%s' %(row+1), 'Generate on', wbf['header_no'])
        worksheet.write('K%s' %(row+1), 'Create by', wbf['header_no'])
        worksheet.write('L%s' %(row+1), 'State', wbf['header_no'])

        if self.status != 'Outstanding':
            worksheet.write('M%s' %(row+1), 'Posted on', wbf['header_no'])
            worksheet.write('N%s' %(row+1), 'Posted by', wbf['header_no'])

        row +=2
        
        no = 1
        row1 = row

        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])  
            worksheet.write('B%s' % row, res.get('code') , wbf['content'])                    
            worksheet.write('C%s' % row, res.get('branch') , wbf['content'])
            worksheet.write('D%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('E%s' % row, res.get('tgl_so') , wbf['content'])
            worksheet.write('F%s' % row, res.get('division') , wbf['content'])
            worksheet.write('G%s' % row, res.get('staff_bbn') , wbf['content']) 
            worksheet.write('H%s' % row, res.get('adh') , wbf['content'])
            worksheet.write('I%s' % row, res.get('soh') , wbf['content'])
            worksheet.write('J%s' % row, res.get('generate_date') , wbf['content'])
            worksheet.write('K%s' % row, res.get('create_by') , wbf['content'])
            worksheet.write('L%s' % row, res.get('state') , wbf['content'])
            if self.status != 'Outstanding':
                worksheet.write('M%s' % row, res.get('post_on') , wbf['content'])
                worksheet.write('N%s' % row, res.get('post_by') , wbf['content'])        
            no +=1
            row +=1                    
        
        if self.status != 'Outstanding':
            worksheet.autofilter('A5:N%s' % (row))
            worksheet.merge_range('A%s:N%s' % (row,row), '', wbf['total'])
        else:
            worksheet.autofilter('A5:L%s' % (row))
            worksheet.merge_range('A%s:L%s' % (row,row), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_stock_opname.view_teds_laporan_stock_opname_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.stock.opname.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def laporan_so_bpkb(self):
        query_where = " WHERE 1=1"
        if self.status == 'Outstanding':
            query_where += " AND sot.state = 'draft'"
        if self.status == 'Done':
            query_where += " AND sot.state = 'posted'"
        if self.branch_ids:
            branch_ids = [b.id for b in self.branch_ids]   
            query_where +=" AND sot.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if self.periode and self.tahun:
            query_where +=" AND to_char(sot.date,'MM') = '%s' AND to_char(sot.date,'YYYY') = '%s'" %(self.periode,self.tahun)


        query = """
            SELECT 
            b.code as code
            , b.name as branch
            , sot.name as no_so
            , sot.staff_bbn
            , sot.adh
            , sot.soh
            , sot.date as tgl_so
            , sot.division
            , sot.generate_date
            , cp.name as create_by
            , sot.create_date as create_on
            , posp.name as post_by
            , sot.post_date as post_on
            , sot.state
            FROM teds_stock_opname_bpkb sot
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN res_users c ON c.id = sot.create_uid
            INNER JOIN res_partner cp ON cp.id = c.partner_id 
            LEFT JOIN res_users pos ON pos.id = sot.post_uid
            LEFT JOIN res_partner posp ON posp.id = pos.partner_id 
            %s
        """ % (query_where)

        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('BPKB')
        worksheet.set_column('B1:B1',6)
        worksheet.set_column('C1:C1',22)
        worksheet.set_column('D1:D1',22)
        worksheet.set_column('E1:E1',13)
        worksheet.set_column('F1:F1',13)
        worksheet.set_column('G1:G1',24)
        worksheet.set_column('H1:H1',24)
        worksheet.set_column('I1:I1',24)
        worksheet.set_column('J1:J1',24)
        worksheet.set_column('K1:K1',24)
        worksheet.set_column('L1:L1',12)
        worksheet.set_column('M1:M1',24)
        worksheet.set_column('N1:N1',24)



        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname BPKB %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Stock Opname BPKB', wbf['company'])
        worksheet.merge_range('A2:C2', 'Periode %s %s'%(calendar.month_name[int(self.periode)],self.tahun), wbf['company'])
        worksheet.merge_range('A3:C3', 'Status %s'%(self.status), wbf['company'])
 
        row=4
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'Code', wbf['header_no'])
        worksheet.write('C%s' %(row+1), 'Cabang', wbf['header_no'])
        worksheet.write('D%s' %(row+1), 'No SO', wbf['header_no'])
        worksheet.write('E%s' %(row+1), 'Tgl SO', wbf['header_no'])
        worksheet.write('F%s' %(row+1), 'Division', wbf['header_no'])
        worksheet.write('G%s' %(row+1), 'Staff BBN', wbf['header_no'])
        worksheet.write('H%s' %(row+1), 'ADH', wbf['header_no'])
        worksheet.write('I%s' %(row+1), 'SOH', wbf['header_no'])
        worksheet.write('J%s' %(row+1), 'Generate on', wbf['header_no'])
        worksheet.write('K%s' %(row+1), 'Create by', wbf['header_no'])
        worksheet.write('L%s' %(row+1), 'State', wbf['header_no'])

        if self.status != 'Outstanding':
            worksheet.write('M%s' %(row+1), 'Posted on', wbf['header_no'])
            worksheet.write('N%s' %(row+1), 'Posted by', wbf['header_no'])

        row +=2
        
        no = 1
        row1 = row

        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])  
            worksheet.write('B%s' % row, res.get('code') , wbf['content'])                    
            worksheet.write('C%s' % row, res.get('branch') , wbf['content'])
            worksheet.write('D%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('E%s' % row, res.get('tgl_so') , wbf['content'])
            worksheet.write('F%s' % row, res.get('division') , wbf['content'])
            worksheet.write('G%s' % row, res.get('staff_bbn') , wbf['content']) 
            worksheet.write('H%s' % row, res.get('adh') , wbf['content'])
            worksheet.write('I%s' % row, res.get('soh') , wbf['content'])
            worksheet.write('J%s' % row, res.get('generate_date') , wbf['content'])
            worksheet.write('K%s' % row, res.get('create_by') , wbf['content'])
            worksheet.write('L%s' % row, res.get('state') , wbf['content'])
            if self.status != 'Outstanding':
                worksheet.write('M%s' % row, res.get('post_on') , wbf['content'])
                worksheet.write('N%s' % row, res.get('post_by') , wbf['content'])

            no +=1
            row +=1                    
           
        if self.status != 'Outstanding':
            worksheet.autofilter('A5:N%s' % (row))
            worksheet.merge_range('A%s:N%s' % (row,row), '', wbf['total'])
        else:
            worksheet.autofilter('A5:L%s' % (row))
            worksheet.merge_range('A%s:L%s' % (row,row), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_stock_opname.view_teds_laporan_stock_opname_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.stock.opname.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    
      
   



