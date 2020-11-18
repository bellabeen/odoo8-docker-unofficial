import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
  
class wtc_stock_production_lot_wizard_permohonan_faktur(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
                'permohonan_faktur_id': fields.many2one('wtc.permohonan.faktur',string="No Permohonan Faktur", track_visibility='always'), 
                'penerimaan_faktur_id': fields.many2one('wtc.penerimaan.faktur',string="No Penerimaan Faktur"), 
                'tgl_cetak_faktur' : fields.date('Tgl Cetak Faktur'),
                'cddb_id' : fields.many2one('wtc.cddb',domain="[('customer_id','=',customer_id)]",string="CDDB"),
                'lot_status_cddb' : fields.selection([('not','Not Ok'),('ok','OK'),('udstk','UDSTK OK'),('cddb','CDDB OK')],string="CDDB State"),
                #BPKB
                'invoice_bbn' : fields.many2one('account.invoice','Invoice BBN',domain=[('type','=','in_invoice')]),
                'tgl_bayar_birojasa' : fields.date('Tgl Bayar Biro Jasa'),
                'tgl_penyerahan_faktur' : fields.date('Tgl Penyerahan Faktur'),
                'penyerahan_faktur_id' : fields.many2one('wtc.penyerahan.faktur',string="No Penyerahan Faktur"), 
            }
    
    _track = {
        'state_stnk': {
            'wtc_permohonan_faktur.mt_lot_state_stnk_mohon_stnk': lambda self, cr, uid, obj, ctx=None: obj.state_stnk == 'mohon_faktur',
        },
        'state': {
            'wtc_permohonan_faktur.mt_lot_state_paid': lambda self, cr, uid, obj, ctx=None: obj.state == 'paid',
        },                             
    } 
        
    _defaults = {
                'lot_status_cddb':'not'
                }
    def get_customer_database(self,cr,uid,ids,context=None):
        vals = self.browse(cr,uid,ids)
        form_id  = 'wtc.cddb.wizard.form.view'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'wtc.cddb'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        return {
            'name': 'Form CDDB',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.cddb',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': vals.cddb_id.id
            } 
    
    def get_atasnama_stnk(self,cr,uid,ids,context=None):
        warn = {}
        vals = self.browse(cr,uid,ids)
        form_id  = 'wtc.atas.nama.stnk.wizard.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'res.partner'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        udstk = vals.customer_stnk.id
        if udstk :
            return {
                'name': 'Customers',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'view_id' : form_browse.id,
                'nodestroy': True,
                'target': 'new',
                'res_id': udstk
                } 
        else :
            return False

    def get_edit_udstk(self,cr,uid,ids,context=None):
        vals = self.browse(cr,uid,ids)
        form_id  = 'edit.udstk.wizard.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'stock.production.lot'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        return {
            'name': 'UDSTNK',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.production.lot',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': vals.id
            } 

