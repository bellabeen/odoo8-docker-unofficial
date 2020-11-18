import time 
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree
from pytz import timezone
from openerp.exceptions import except_orm, Warning, RedirectWarning

class MonitoringHotlineWizard(models.TransientModel):
    _name = "teds.part.hotline.monitoring.wizard"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False
   
    def _get_default_date(self):
        return date.today()

    @api.one
    @api.depends('detail_ids')
    def cek_is_report(self):
        if len(self.detail_ids) > 0:
            self.is_report = True

    branch_ids = fields.Many2many('wtc.branch','teds_part_hotline_monitoring_rel', 'monitorind_id', 'branch_id', 'Branch',default=_get_default_branch)
    is_report = fields.Boolean('Is Report',compute='cek_is_report')
    options = fields.Selection([
        ('periode','Periode'),
        ('hotline','No Hotline')])
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    no_hotline = fields.Char('No Hotline')
    detail_ids = fields.One2many('teds.part.hotline.monitoring.detail.wizard','monitoring_id')
    
    @api.onchange('no_hotline')
    def onchange_no_hotline(self):
        if self.no_hotline:
            self.no_hotline = self.no_hotline.strip().upper()
    
    @api.onchange('options')
    def onchange_optios(self):
        self.start_date = False
        self.end_date = False
        self.no_hotline = False
        if self.options == 'hotline':
            self.start_date = False
            self.end_date = False
        elif self.options == 'periode':
            self.no_hotline = False

    @api.multi
    def action_search(self):
        self.detail_ids = False
        start_date = self.start_date
        end_date = self.end_date
        branch_ids = self.branch_ids
        no_hotline = self.no_hotline

        WHERE = " WHERE (hd.no_po IS NULL OR hd.no_wo IS NULL) AND h.state != 'cancel'"
        if self.options == 'periode':
            WHERE += " AND h.date >= '%s' AND h.date <= '%s'"%(start_date,end_date)
        elif self.options == 'hotline':            
            WHERE += " AND h.name = '%s'" %str(no_hotline)
        
        if branch_ids:
            WHERE += " AND h.branch_id in %s"%str(tuple([b.id for b in branch_ids])).replace(',)', ')')

        query = """
            SELECT h.name as hotline
            , h.lot_id as lot_id
            , h.customer_id as customer_id
            , h.pembawa as pembawa
            , h.no_telp as no_telp
            , hd.product_id as product_id
            , hd.qty as hotline_qty
            , hd.no_po as po
            , hd.qty_spl as po_qty
            , hd.no_wo as wo
            , hd.qty_wo as wo_qty
            , CASE WHEN hd.no_po is not null THEN True ELSE False END as is_po
            , CASE WHEN hd.no_wo is not null THEN True ELSE False END as is_wo
            , am.name || '(' ||hl.name|| ')' as hl
            , dp.amount_hl_allocation as amount
            , to_char(po.date_order,'YYYY-MM-DD') as tgl_po
            , h.date as tgl_hotline
            , COALESCE(date_part('days',now() - COALESCE(po.date_order,hd.tgl_po)),0) as umur
            FROM teds_part_hotline h
            INNER JOIN teds_part_hotline_detail hd ON hd.hotline_id = h.id
            LEFT JOIN teds_part_hotline_alokasi_dp dp ON dp.hotline_id = h.id
            LEFT JOIN account_move_line hl ON hl.id = dp.hl_id
            LEFT JOIN account_move am ON am.id = hl.move_id
            LEFT JOIN purchase_order po ON po.part_hotline_id = h.id
            %s
            ORDER BY h.name,hd.no_po,hd.no_wo asc
        """ %(WHERE)
        self._cr.execute (query)
        ress =  self._cr.dictfetchall()

        datas = {}
        for res in ress:
            hotline = res.get('hotline')
            if not datas.get(hotline):
                datas[hotline] = {
                    'name': hotline,
                    'lot_id': res['lot_id'],
                    'customer_id': res['customer_id'],
                    'pembawa': res['pembawa'],
                    'no_telp': res['no_telp'],
                    'is_wo': res['is_wo'],
                    'is_po': res['is_po'],
                    'tgl_po':res['tgl_po'],
                    'tgl_hotline':res['tgl_hotline'],
                    'umur':int(res['umur']),
                    'line_ids': [
                        [0,False,{
                            'product_id':res['product_id'],
                            'qty':res['hotline_qty'],
                            'qty_wo':res['wo_qty'],
                            'qty_po':res['po_qty'],
                            'no_wo':res['wo'],
                            'no_po':res['po'],
                  
                        }]
                    ]
                }
                if res.get('hl'):
                    datas[hotline]['dp_ids'] = [
                        [0,False,{
                            'name':res['hl'],
                            'amount_alokasi':res['amount']
                        }]
                    ]
                    datas[hotline]['hl_ids'] = [res['hl']]

                datas[hotline]['product_ids'] = [res['product_id']]
            else:
                if res['product_id'] not in datas[hotline]['product_ids']:
                    datas[hotline]['line_ids'].append([0,False,{
                        'product_id':res['product_id'],
                        'qty':res['hotline_qty'],
                        'qty_wo':res['wo_qty'],
                        'qty_po':res['po_qty'],                   
                        'no_wo':res['wo'],
                        'no_po':res['po'],
                    }])
                    datas[hotline]['product_ids'].append(res['product_id'])
                
                if res.get('hl'):
                    if res['hl'] not in datas[hotline]['hl_ids']:
                        datas[hotline]['dp_ids'].append([0,False,{
                            'name':res['hl'],
                            'amount_alokasi':res['amount']    
                        }])
                        datas[hotline]['hl_ids'].append(res['hl'])
        ids = []
        for data in datas.values():
            ids.append([0,False,data])

        self.detail_ids = ids
    
    @api.multi
    def action_xls(self):
        raise Warning('Belum tersedia !')
    
    @api.multi
    def action_csv(self):
        raise Warning('Belum tersedia !')

class MonitoringHotlineDetailWizard(models.TransientModel):
    _name = "teds.part.hotline.monitoring.detail.wizard"

    monitoring_id = fields.Many2one('teds.part.hotline.monitoring.wizard',ondelete='cascade')
    name = fields.Char('No Hotline')
    lot_id = fields.Many2one('stock.production.lot', 'No Engine')
    chassis_no = fields.Char('No Chassis',related='lot_id.chassis_no',readonly=True)
    no_pol = fields.Char('No Polisi',related='lot_id.no_polisi',readonly=True)
    customer_id = fields.Many2one('res.partner','Customer')
    pembawa = fields.Char('Pembawa')
    no_telp = fields.Char('No Telp')
    line_ids = fields.One2many('teds.part.hotline.monitoring.detail.line.wizard','detail_id')
    dp_ids = fields.One2many('teds.part.hotline.monitoring.dp.wizard','detail_id')
    is_po = fields.Boolean('Sudah PO ?')
    is_wo = fields.Boolean('Sudah WO ?')
    tgl_hotline = fields.Date('Tgl Hotline')
    tgl_po = fields.Date('Tgl PO')
    umur = fields.Char('Umur')

class MonitoringHotlineDPWizard(models.TransientModel):
    _name = "teds.part.hotline.monitoring.dp.wizard"

    detail_id = fields.Many2one('teds.part.hotline.monitoring.detail.wizard',ondelete='cascade')
    name = fields.Char('Hutang Lain')
    amount_alokasi = fields.Float('Alokasi')

class MonitoringHotlineDetailLineWizard(models.TransientModel):
    _name = "teds.part.hotline.monitoring.detail.line.wizard"

    detail_id = fields.Many2one('teds.part.hotline.monitoring.detail.wizard',ondelete='cascade')
    product_id = fields.Many2one('product.product','Product')
    name = fields.Char('Description',related="product_id.default_code",readonly=True)
    qty = fields.Float('Qty')
    qty_po = fields.Float('Qty PO')
    qty_wo = fields.Float('Qty WO')
    no_wo = fields.Char('No WO')
    no_po = fields.Char('No PO')
    





        
