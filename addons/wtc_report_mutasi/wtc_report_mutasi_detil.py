import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree


class wtc_report_mutasi_detil(osv.osv_memory):
    _name='wtc.report.mutasi.detil'

    wbf={}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_mutasi_detil, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Sparepart')

        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_ids']")

        for node in nodes:
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')

        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'division':fields.selection([('Sparepart','Sparepart'),('Unit','Unit')]),
        'options':fields.selection([('mutation_order_detil','Mutation Order Detil')]),
        'state': fields.selection([('all','All'), ('confirm','Confirmed'), ('done','Done')]),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_mutasi_detil_rel', 'wtc_report_mutasi_detil_wizard_id','branch_id', 'Branch', copy=False),
        'product_ids': fields.many2many('product.product', 'wtc_report_mutasi_detil_product_rel', 'wtc_report_mutasi_detil_wizard_id','product_id', 'Product', copy=False, ),
        'type_file': fields.selection([('excel','Excel'),('csv','CSV')],string="Format File")
        }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'state':'all',
        'type_file':'excel',
        }

        
    def add_workbook_format(self, cr, uid, workbook):      
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

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
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

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})

        return self._print_excel_report_mutasi_part_detil(cr, uid,ids,data,context=context)
        # ir_model_data = self.pool.get('ir.model.data')
        # form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_mutasi_detil')

        # form_id = form_res and form_res[1] or False
        # return {
        #     'name': _('Download XLS'),
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'wtc.report.mutasi.detil',
        #     'res_id': ids[0],
        #     'view_id': False,
        #     'views': [(form_id, 'form')],
        #     'type': 'ir.actions.act_window',
        #     'target': 'current'
        # }
    def get_hpp(self,cr,uid,ids,product_id,warehouse_id,confirm_date):

        query_hpp="""
        SELECT cost 
        FROM product_price_history_branch pphb
        WHERE product_id = %s
        AND warehouse_id = %s
        AND pphb.datetime = (
            SELECT MAX(datetime) 
            FROM product_price_history_branch
            WHERE product_id = %s
            AND warehouse_id = %s
            AND datetime + interval '7 hours' <= '%s'
            LIMIT 1
        )
        LIMIT 1
        """ %(product_id,warehouse_id,product_id,warehouse_id,confirm_date)
        cr.execute (query_hpp)
        result = cr.fetchall()
        for res in result:
            return res[0]
      
       

    def _print_excel_report_mutasi_part_detil(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        division=data['division']
        state=data['state']
        type_file=data['type_file']
                      
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""
        if branch_ids :
            query_where += " and mo.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 

        if division:
            query_division = " and mo.division ='%s' " %(division)

        if state=='confirm':
            query_state = " and mo.state ='confirm' "
        elif state=='done':
            query_state = " and mo.state ='done' "
        else:
            query_state = " "

        query="""
            select b.code
            , b.name
            , mo.name 
            , mo.state 
            , mo.confirm_date + interval '7 hours' as confirm_date
            , b2.code
            , b2.name 
            , p.name_template
            , pav.code 
            , p.default_code
            , pt.description
            , case when mo.state = 'cancelled' then -1 * mol.qty else mol.qty end as qty
            , 0 as hpp
            , mol.unit_price as het
            , mol.unit_price / 1.1 as harga_jual
            , pc.name as categ1
            , coalesce(pc2.name, '') as categ2
            , mo.division
            , mol.product_id
            , b.warehouse_id
            , mol.supply_qty
            from wtc_mutation_order mo
            inner join wtc_mutation_order_line mol on mol.order_id = mo.id
            inner join wtc_branch b on b.id = mo.branch_id
            left join wtc_branch b2 on b2.id = mo.branch_requester_id
            left join product_product p on p.id = mol.product_id 
            left join product_template pt on pt.id = p.product_tmpl_id
            left join product_category pc on pc.id = pt.categ_id
            left join product_category pc2 on pc2.id = pc.parent_id
            left join product_attribute_value_product_product_rel pavpp ON p.id = pavpp.prod_id 
            left join product_attribute_value pav ON pavpp.att_id = pav.id 
            where ((mo.state in ('done', 'confirm') and mo.date >= '%s' and mo.date <= '%s') 
            or (mo.state in ('cancelled') and mo.cancelled_date + interval '7 hours' >= '%s' and mo.cancelled_date + interval '7 hours' <= '%s'))
             %s %s %s
            """ % (start_date,end_date,start_date,end_date,query_division,query_where,query_state)

        cr.execute (query)
        ress = cr.fetchall()

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")

        if type_file == 'csv':
            content = "Branch Code,Branch Name,Division,Mutation Order,State,Confirm Date,Branch Req Code,Branch Req Name,Name Template,PAV Code,Default Code,Description,Qty,Hpp,HET,Harga Jual,Tot Hpp,Tot Harga Jual,Categ1,Categ2,Suply Qty,Undelivered \r\n"
            for res in ress:
                branch_code=res[0]
                branch_name = res[1]
                mo = res[2]
                state = res[3].encode('ascii','ignore').decode('ascii')
                confirm_date =  res[4].encode('ascii','ignore').decode('ascii')
                branch_req_code =res[5]
                branch_req_name = res[6]
                name_template =res[7]
                pav_code=res[8]
                default_code=res[9]
                descp=res[10]
                qty=res[11]
                hpp=res[12]
                het=res[13]
                harga_jual=res[14]
                categ1=res[15]
                categ2=res[16]
                division=res[17]
                product_id=res[18]
                warehouse_id=res[19]
                if res[20]:
                    supply_qty=res[20]
                else:
                    supply_qty=0
                undelivered=qty-supply_qty
                get_hpp=self.get_hpp(cr, uid, ids,product_id,warehouse_id,confirm_date)
                total_hpp = 0
                if total_hpp != 0:
                    total_hpp = qty * get_hpp

                total_harga_jual = 0
                if het != 0:
                    total_harga_jual = qty * het

                content += "%s," %branch_code
                content += "%s," %branch_name
                content += "%s," %division
                content += "%s," %mo
                content += "%s," %state
                content += "%s," %confirm_date
                content += "%s," %branch_req_code
                content += "%s," %branch_req_name
                content += "%s," %name_template
                content += "%s," %pav_code
                content += "%s," %default_code.replace(',','')
                content += "%s," %descp.replace(',','')
                content += "%s," %qty
                content += "%s," %get_hpp
                content += "%s," %het
                content += "%s," %harga_jual
                content += "%s," %total_hpp
                content += "%s," %total_harga_jual
                content += "%s," %categ1
                content += "%s," %categ2
                content += "%s," %supply_qty
                content += "%s \r\n" %undelivered

            filename = 'Report Mutasi Detil '+str(date)+'.csv'
            out = base64.encodestring(content)

        else:
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp)        
            workbook = self.add_workbook_format(cr, uid, workbook)
            wbf=self.wbf
            worksheet = workbook.add_worksheet('%s' %(division)) 
            worksheet.set_column('B1:B1', 15)
            worksheet.set_column('C1:C1', 25)
            worksheet.set_column('D1:D1', 10)
            worksheet.set_column('E1:E1', 20)
            worksheet.set_column('F1:F1', 10)
            worksheet.set_column('G1:G1', 30)
            worksheet.set_column('H1:H1', 15)
            worksheet.set_column('I1:I1', 25)
            worksheet.set_column('J1:J1', 20)
            worksheet.set_column('K1:K1', 10)    
            worksheet.set_column('L1:L1', 30)    
            worksheet.set_column('M1:M1', 30)    
            worksheet.set_column('N1:N1', 5)    
            worksheet.set_column('O1:O1', 20)    
            worksheet.set_column('P:P', 20)    
            worksheet.set_column('Q:Q', 20)    
            worksheet.set_column('R:R', 20)    
            worksheet.set_column('S:S', 20)    
            worksheet.set_column('T:T', 20)    
            worksheet.set_column('U:U', 20)
            worksheet.set_column('V:V', 20)    
            worksheet.set_column('W:W', 20)    
                            
            company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
            user = self._get_default(cr, uid, user=True, context=context).name
            
            filename = 'Report Mutasi Detil '+str(date)+'.xlsx'        
            worksheet.write('A1', company_name , wbf['company'])
            worksheet.write('A2', 'Report Mutasi Detil (%s)' %(division) , wbf['title_doc'])
            worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
                    
            
            row=4
            colstr=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP','AQ','AR','AS','AT','AU','AV','AW','AX','AY','AZ','BA','BB','BC','BD','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP','BQ','BR','BS','BT','BU','BV','BW','BX','BY','BZ']
            col=0
            worksheet.write('%s%s' % (colstr[col],row+1), 'No' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Branch Code' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1), 'Branch Name' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Division' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Mutation Order' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'State' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Confirm Date' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Branch Req Code' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Branch Req Name' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Name Template' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'PAV Code' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Default Code' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Description' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Qty' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Hpp' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'HET' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Harga Jual' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Tot Hpp' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Tot Harga Jual' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Categ1' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Categ2' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Suply Qty' , wbf['header'])
            col+=1
            worksheet.write('%s%s' % (colstr[col],row+1),  'Undelivered' , wbf['header'])
               
            row+=2               
            no = 1     
            row1 = row
            
            supply_qty=0
            qty=0
            for res in ress:
                branch_code=res[0]
                branch_name = res[1]
                mo = res[2]
                state = res[3].encode('ascii','ignore').decode('ascii')
                confirm_date =  res[4].encode('ascii','ignore').decode('ascii')
                branch_req_code =res[5]
                branch_req_name = res[6]
                name_template =res[7]
                pav_code=res[8] if res[8] else ''
                default_code=res[9]
                descp=res[10]
                qty=res[11]
                hpp=res[12]
                het=res[13]
                harga_jual=res[14]
                categ1=res[15]
                categ2=res[16]
                division=res[17]
                product_id=res[18]
                warehouse_id=res[19]
                if res[20]:
                    supply_qty=res[20]
                else:
                    supply_qty=0
                undelivered=qty-supply_qty

                get_hpp=self.get_hpp(cr, uid, ids,product_id,warehouse_id,confirm_date)
                col=0
                worksheet.write('%s%s' % (colstr[col],row), no , wbf['content_number'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), branch_code , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), branch_name , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), division , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), mo , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), state , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), confirm_date , wbf['content_date'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), branch_req_code , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), branch_req_name, wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), name_template , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), pav_code , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), default_code , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), descp , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), qty , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), get_hpp , wbf['content_float'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), het , wbf['content_float'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), harga_jual , wbf['content_float'])
                col+=1
                worksheet.write_formula('%s%s' % (colstr[col],row), '=N%s*O%s' % (row, row), wbf['content_float'])
                col+=1
                worksheet.write_formula('%s%s' % (colstr[col],row), '=N%s*Q%s' % (row, row), wbf['content_float'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), categ1 , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), categ2 , wbf['content'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), supply_qty , wbf['content_float'])
                col+=1
                worksheet.write('%s%s' % (colstr[col],row), undelivered , wbf['content_float'])

                no+=1
                row+=1

                    
            worksheet.autofilter('A5:R%s' % (row))  
            worksheet.freeze_panes(5, 3)
            worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

            workbook.close()
            out=base64.encodestring(fp.getvalue())
            fp.close()

        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_mutasi', 'wtc_report_mutasi_detil')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.mutasi.detil',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

        return true



wtc_report_mutasi_detil()