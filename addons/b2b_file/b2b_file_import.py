from openerp import models, fields, api, _
import fnmatch
import os
import os, sys
import shutil
import time
import smtplib
from __builtin__ import str
from openerp import workflow
from datetime import datetime
import base64
from openerp.exceptions import except_orm, Warning, RedirectWarning

class b2b_file_import(models.Model):
    _name = "b2b.file.import"
    _description = "B2B File Import"
    data=fields.Binary(string="File")
    type = fields.Selection([
                    ('inv', 'INV'),                                
                    ('sl', 'SL'),
                    ('sipb', 'SIPB'),
                    ('fm', 'FM'),
                    ('fdo', 'FDO'),
                    ('ps', 'PS'),
                    ('pmp', 'PMP'),
                    ('ptrac','PTRAC'),
                    ('psl','PSL'),
                    ],string='Type File',required=True)
    
    @api.multi
    def import_file(self):
        if self.type == 'inv':
            self.action_import_inv(self.data)
        elif self.type == 'sl':
            self.action_import_sl(self.data)
        elif self.type == 'sipb':
            self.action_import_sipb(self.data)
        elif self.type == 'fm':
            self.action_import_fm(self.data)
        elif self.type == 'ps':
            self.action_import_ps(self.data)
        elif self.type == 'pmp':
            self.action_import_pmp(self.data)
        elif self.type == 'ptrac':
            self.action_import_ptrac(self.data)
        elif self.type == 'psl':
            self.action_import_psl(self.data)
        
    def action_import_ptrac(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:
            line = n.split(';')

            if (line[0] == ''):
                del line
                break
            month_deliver = line[7][0:4]+"-"+line[7][4:6]+"-"+line[7][6:8]
            dmodi = line[12][0:4]+"-"+line[12][4:6]+"-"+line[12][6:8]
            dcrea = line[13][0:4]+"-"+line[13][4:6]+"-"+line[13][6:8]

    

            obj_check_double=self.env['b2b.file.ptrac'].search([
                                                                ('no_po_ahm','=',line[0]),
                                                                ('part_no','=',line[1]),
                                                                ('qq_ship_to','=',line[2]),
                                                                ('kode_md','=',line[3]),
                                                                ('kode_order','=',line[4]),
                                                                ('qty_po','=',line[5]),
                                                                ('qty_shipping','=',line[6]),
                                                                ('month_deliver','=',month_deliver),
                                                                ('no_po_md','=',line[8]),
                                                                ('qty_book','=',line[9]),
                                                                ('qty_packing','=',line[10]),
                                                                ('qty_picking','=',line[11]),
                                                                ('dmodi','=',dmodi),
                                                                ('dcrea','=',dcrea),
                                                                ('flag_fast_slow','=',line[14]),
                                                                ('qty_invoice','=',line[15]),
                                                                ('flag_additional','=',line[16]),
                                                               ])
            if obj_check_double :
                raise Warning(('Perhatian !'), ('Maaf Data PTRAC Yang di Import Sudah Ada !')) 
            else :

                ptrac = {
                        'no_po_ahm':line[0],
                        'part_no':line[1],
                        'qq_ship_to':line[2],
                        'kode_md':line[3],
                        'kode_order':line[4],
                        'qty_po':line[5],
                        'qty_shipping':line[6],
                        'month_deliver':month_deliver,
                        'no_po_md':line[8],
                        'qty_book':line[9],
                        'qty_packing':line[10],
                        'qty_picking':line[11],
                        'dmodi':dmodi,
                        'dcrea':dcrea,
                        'flag_fast_slow':line[14],
                        'qty_invoice':line[15],
                        'flag_additional':line[16],                   
                    }
                ptrac_id=self.env['b2b.file.ptrac'].create(ptrac)      
                
    def action_import_psl(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:
            line = obj.name.split()

            if (line == []):
                del line
                break
                
            dat1 = line[0:4]
            dat2 = line[-3:]
            del line[0:4]
            del line[-3:]
            dat3 = ' '.join(line)
            data = dat1+dat2
            data.append(dat3)
            
            kode = data[0][0:1]
            kode_md = data[0][1:]
            tanggal_psl = data[1][4:8]+"-"+data[1][2:4]+"-"+data[1][0:2]
            kode_psl = data[1][8:23]
            kode_po_md = data[1][23:]
            type_po = data[2][0:3]
            tgl_po = data[2][7:11]+"-"+data[2][5:7]+"-"+data[2][3:5]
            no_urut = data[2][11:]
            kode_dus = data[3][0:15]
            kode_sparepart = data[3][15:]
            desc_sparepart = data[7]
            qty_psl = data[4]
            qty_po = data[5]
            remaining_qty = data[6]   
            
            print kode
            print kode_md
            print tanggal_psl
            print kode_psl
            print kode_po_md
            print type_po
            print tgl_po
            print no_urut
            print kode_dus
            print kode_sparepart
            print desc_sparepart
            print qty_psl
            print qty_po
            print remaining_qty

           
            psl = {
                'kode':kode,
                'kode_md':kode_md,
                'tanggal_psl':tanggal_psl,
                'kode_psl':kode_psl,
                'kode_po_md':kode_po_md,
                'type_po':type_po,
                'tgl_po':tgl_po,
                'no_urut':no_urut,
                'kode_dus':kode_dus,
                'kode_sparepart':kode_sparepart,
                'desc_sparepart':desc_sparepart,
                'qty_psl':qty_po,
                'qty_po':qty_psl,
                'remaining_qty':remaining_qty,
            }                
       
            psl_id = self.create(psl) 
        
            ps = self.env['b2b.file.ps']
            src_ps = ps.search ([
                                ('kode_ps','=',kode_psl),
                                ('kode_sparepart','=',kode_sparepart),
                                ('kode_dus','=', kode_dus),
                            ])
            print src_ps
        
            if src_ps:
                ps.browse(src_ps.id).write({'status':'on intransit'})        
         
    def action_import_sl(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:
            line = n.split(';')   
            no_mesin=line[0].replace(" ", "")
            obj_check_double=self.env['b2b.file.sl'].search([('no_mesin','=',no_mesin),('no_rangka','=',line[1])])
            if not obj_check_double :
                tgl_ship_list=line[7][4:]+"-"+line[7][2:4]+"-"+line[7][0:2]
                sl = {
                            'no_mesin': no_mesin,
                            'no_rangka' :line[1],
                            'kode_type':line[2],
                            'kode_warna':line[3],
                            'kode_md' :line[4],
                            'no_sipb' : line[5], 
                            'no_ship_list' : line[6],
                            'tgl_ship_list' : tgl_ship_list,
                            'nopol_expedisi': line[8],
                            'kode_md_qq': line[9],
                            'kode_md_pembuka_po': line[10],                        
                    }
                sl_id=self.env['b2b.file.sl'].create(sl)

    def action_import_sipb(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:  
            line = n.split(';') 
            tgl_sipb=line[1][4:]+"-"+line[1][2:4]+"-"+line[1][0:2]
            tgl_so=line[3][4:]+"-"+line[3][2:4]+"-"+line[3][0:2]
            obj_check_double=self.env['b2b.file.sipb'].search([
                                                               ('no_sipb','=',line[0]),
                                                               ('tgl_sipb','=',tgl_sipb),
                                                               ('no_spes','=',line[2]),
                                                               ('tgl_so','=',tgl_so),
                                                               ('kode_type','=',line[4]),
                                                               ('kode_warna','=',line[5]),
                                                               ('jumlah','=',line[6]),
                                                               ('harga','=',line[7]),
                                                               ('no_po_md','=',line[10]),
                                                               ('amount_total','=',line[12]),
                                                               ('ppn_total','=',line[13]),
                                                               ('pph_total','=',line[14]),
                                                               ])
            if not obj_check_double :
                sipb = {
                        'no_sipb': line[0],
                        'tgl_sipb' :tgl_sipb,
                        'no_spes':line[2],
                        'tgl_so':tgl_so,
                        'kode_type' :line[4],
                        'kode_warna' : line[5], 
                        'jumlah' : line[6],
                        'harga' : line[7],
                        'discount': line[8],
                        'quotation_flag': line[9],
                        'no_po_md': line[10],  
                        'dealer_qq': line[11],
                        'amount_total': line[12],
                        'ppn_total': line[13],
                        'pph_total': line[14],                      
                    }
                sipb_id=self.env['b2b.file.sipb'].create(sipb)      
                
    def action_import_fm(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:  
            line = n.split(';') 
            line = x.name.split(';')
            no_mesin=line[0].replace(" ", "")
            obj_check_double=self.env['b2b.file.fm'].search([('no_mesin','=',no_mesin),('no_rangka','=',line[1])])
            if not obj_check_double :
                tgl_ship_list=line[12][4:]+"-"+line[12][2:4]+"-"+line[12][0:2]
                fm = {
                        'no_mesin': no_mesin,
                        'no_rangka' :line[1],
                        'kode_type':line[2],
                        'kode_warna':line[3],
                        'kode_md' :line[4],
                        'no_faktur' : line[5], 
                        'tahun_produksi' : line[6],
                        'harga_faktur_stnk' : line[7],
                        'no_ppud': line[8],
                        'nama_kapal': line[9],
                        'no_sipb': line[10],
                        'no_ship_list': line[11],
                        'tgl_ship_list': tgl_ship_list,       
                        'nopol_expedisi': line[13],                         
                    }
                fm_id=self.env['b2b.file.fm'].create(fm)    
   
        
    @api.multi
    def action_import_inv(self,data):
            file=base64.decodestring(data)
            ct = file.splitlines()
            purchase_line=False
            for n in ct:
                line = n.split(';')
                tgl_faktur=line[1][4:]+"-"+line[1][2:4]+"-"+line[1][0:2]
                top=line[2][4:]+"-"+line[2][2:4]+"-"+line[2][0:2]
                top_ppn=line[3][4:]+"-"+line[3][2:4]+"-"+line[3][0:2]
                top_pph=line[4][4:]+"-"+line[4][2:4]+"-"+line[4][0:2]
                obj_cek_line_header=self.env['b2b.file.inv.header'].search([
                                                 ('no_faktur','=', line[0]),
                                                 ('tgl_faktur','=', tgl_faktur),
                                                 ('top','=', top),
                                                 ('top_ppn','=', top_ppn),
                                                 ('top_pph','=', top_pph),
                                                 ('total_invoice','=', line[16]),
                                                 ('ppn_total','=', line[17]),
                                                 ('pph_total','=', line[18]),
                                                 ])
          
                if not obj_cek_line_header :
                    inv_header = {
                            'no_faktur': line[0],
                            'tgl_faktur' :tgl_faktur,
                            'top':top,
                            'top_ppn':top_ppn,
                            'top_pph' :top_pph,
                            'total_invoice': line[16],
                            'ppn_total': line[17],
                            'pph_total': line[18]                  
                        }
                    inv_header_id=self.env['b2b.file.inv.header'].create(inv_header)
                    for n in ct:
                        line = n.split(';')
                        obj_sipb=self.env['b2b.file.sipb'].search([('no_sipb','=',line[6]),
                                                                  ('kode_type','=',line[7]),
                                                                  ('kode_warna','=',line[8]),
                                                                  ])
        
                        #TODO UBAH MENJADI QUERY
                        obj_warna=self.env['product.attribute.value'].search([('code','=',line[8])]) 
                        obj_product=self.env['product.product'].search([('name','=',line[7]),('attribute_value_ids','=',obj_warna.id)])
                        if not obj_product :
                            obj_product=self.env['product.product'].search([('name','=',line[7])])
                        
                        product_id = obj_product.id
                        
                        obj_pucrhase_order=self.env['purchase.order'].search([('name','=',obj_sipb.no_po_md)])
                        if obj_pucrhase_order :
                            obj_purchase_order_line=self.env['purchase.order.line'].search([('order_id','=',obj_pucrhase_order.id),('product_id','=',product_id),])
                            if obj_purchase_order_line :                                                      
                                purchase_line=obj_purchase_order_line.id
                            
                        inv_header_line = {
                            'no_ship_list' : line[5], 
                            'purchase_order_line_id':purchase_line,
                            'b2b_file_inv_header_id':inv_header_id.id,
                            'no_sipb' : line[6],
                            'kode_type' : line[7],
                            'kode_warna': line[8],
                            'qty': line[9],
                            'amount': line[10],  
                            'ppn': line[11],
                            'pph': line[12],
                            'discount_quotation': line[13],
                            'discount_type_cash': line[14],
                            'discount_other': line[15],                
                        }
                        inv_header_line_id=self.env['b2b.file.inv.line'].create(inv_header_line)
    @api.multi                    
    def action_import_ps(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for x in ct:
             i = 0
             kode= x.name[:i+1].strip()
             i+=1
             kode_md = x.name[i:i+5].strip()
             i+=5
             tanggal_ps = x.name[i:i+8].strip()
             i+=8
             kode_ps = x.name[i:i+15].strip()
             i+=15
             kode_po_md = x.name[i:i+30].strip()
             i+=30
             type_po = x.name[i:i+3].strip()
             i+=3
             tgl_po = x.name[i:i+8].strip()
             i+=8
             no_urut = x.name[i:i+5].strip()
             i+=5
             kode_dus = x.name[i:i+15].strip()
             i+=15
             kode_sparepart = x.name[i:i+25].strip()
             i+=25
             desc_sparepart = x.name[i:i+30].strip()
             i+=30
             qty_ps = x.name[i:i+10].strip()
             i+=10
             qty_po = x.name[i:i+10].strip()
             i+=10
             remaining_qty = x.name[i:i+10].strip()
             i+=10
             tanggal_ps_fix=tanggal_ps[4:]+"-"+tanggal_ps[2:4]+"-"+tanggal_ps[0:2]
             tgl_po_fix=tgl_po[4:]+"-"+tgl_po[2:4]+"-"+tgl_po[0:2]
             obj_ps_cek=self.env['b2b.file.ps'].search([
                                                        ('kode','=',kode),
                                                        ('kode_md','=',kode_md),
                                                        #('tanggal_ps','=',tanggal_ps_fix),
                                                        ('kode_ps','=',kode_ps),
                                                        ('kode_po_md','=',kode_po_md),
                                                        ('type_po','=',type_po),
                                                        #('tgl_po','=',tgl_po),
                                                        ('no_urut','=',no_urut),
                                                        ('kode_dus','=',kode_dus),
                                                        ('kode_sparepart','=',kode_sparepart),
                                                        ('qty_ps','=',qty_ps),
                                                        ('qty_po','=',qty_po),
                                                        ('remaining_qty','=',remaining_qty),
                                                        ])
     
             obj_check_rekap_ps=self.env['b2b.file.rekap.ps'].search([
                                                                      ('kode_ps','=',kode_ps),
                                                                      ('kode_sparepart','=',kode_sparepart),
                                                                      ])

             if not obj_check_rekap_ps :
                 ps_rekap={
                           'kode_ps':kode_ps,
                           'kode_sparepart': kode_sparepart,
                           'desc_sparepart': desc_sparepart,
                           'qty_ps': qty_ps,
                           }
                 ps_rekap_id=self.env['b2b.file.rekap.ps'].create(ps_rekap)
             else :
                 total_qty_ps=obj_check_rekap_ps.qty_ps+float(qty_ps)
                 obj_check_rekap_ps.write({'qty_ps':total_qty_ps})
             
             if not obj_ps_cek :
                 ps = {
                     'kode':kode,
                     'kode_md': kode_md,
                     'tanggal_ps':tanggal_ps_fix,
                     'kode_ps':kode_ps,
                     'kode_po_md' :kode_po_md,
                     'type_po' : type_po, 
                     'tgl_po' : tgl_po_fix,
                     'no_urut' : no_urut,
                     'kode_dus': kode_dus,
                     'kode_sparepart': kode_sparepart,
                     'desc_sparepart': desc_sparepart,
                     'qty_ps': qty_ps,       
                     'qty_po': qty_po,    
                     'remaining_qty': remaining_qty,                   
                     }
                 ps_id=self.create(ps)
                 
                 
    @api.multi                    
    def action_import_pmp(self,data): 
        file=base64.decodestring(data)
        ct = file.splitlines()
        for n in ct:
                line = n.split(';') 
                obj_sparepart=self.env['b2b.file.sparepart.pmp'].search([('kode_sparepart','=',line[0])])
                if not obj_sparepart :
                    pmp = {
                            'kode_sparepart': line[0],
                            'desc_sparepart' :line[1],
                            'het':line[2],
                            'hpp':line[3],
                            'supplier' :line[4],
                            'sub_category' : line[5], 
                            'desc_sparepart_2' : line[6],
                            'kolom_8' : line[7],
                            'kolom_9': line[8],
                            'kolom_10': line[9],
                            'kolom_11': line[10],  
                            'kolom_12': line[11],
                            'kolom_13': line[12],
                            'kolom_14': line[13],
                            'kolom_15': line[14], 
                            'kolom_16': line[15],
                            'kolom_17': line[16],
                            'kolom_18': line[17],
                            'kolom_19': line[18],
                            'kolom_20': line[19],                    
                        }
                    pmp_id=self.env['b2b.file.sparepart.pmp'].create(pmp)
                else :
                    obj_sparepart.write({'het':line[2],
                                        'hpp':line[3],
                                        'supplier' :line[4],
                                        'sub_category' : line[5], 
                                        'desc_sparepart_2' : line[6],
                                        'kolom_8' : line[7],
                                        'kolom_9': line[8],
                                        'kolom_10': line[9],
                                        'kolom_11': line[10],  
                                        'kolom_12': line[11],
                                        'kolom_13': line[12],
                                        'kolom_14': line[13],
                                        'kolom_15': line[14], 
                                        'kolom_16': line[15],
                                        'kolom_17': line[16],
                                        'kolom_18': line[17],
                                        'kolom_19': line[18],
                                        'kolom_20': line[19], 
                                         })
                obj_product=self.env['product.template'].search([('name','=',line[0])]) 
                if line[5] == '' :
                    line[5] = 'Sparepart'
                obj_product_category=self.env['product.category'].search([('name','=',line[5])]) 
                if not obj_product :
                    product_sparepart ={
                                        'name':line[0],
                                        'sale_ok':True,
                                        'purchase_ok':True,
                                        'type':'product',
                                        'list_price':12343,
                                        'description':line[6],
                                        'default_code':line[1],
                                        'active':True,
                                        'cost_method':'average',
                                        'sale_delay':'7',
                                        'categ_id':obj_product_category.id,
                                        'valuation':'real_time'
                                        }
                   
                    product_sparepart_id=self.env['product.template'].sudo().create(product_sparepart)
                    product_sparepart_id.write({'list_price':line[2]})
                else :
                    obj_product.write({'name':line[0],
                                        'sale_ok':True,
                                        'purchase_ok':True,
                                        'type':'product',
                                        'list_price':line[2],
                                        'description':line[6],
                                        'default_code':line[1],
                                        'active':True,
                                        'cost_method':'average',
                                        'sale_delay':'7',
                                        'categ_id':obj_product_category.id,
                                        'valuation':'real_time'
                                         })
          
                     