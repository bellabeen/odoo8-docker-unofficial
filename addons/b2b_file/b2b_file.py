from openerp import models, fields, api, _
from openerp.osv import osv
import fnmatch
import os
import os, sys
import shutil
import time
import smtplib
from __builtin__ import str
from openerp import workflow, exceptions
from datetime import datetime

class b2b_file(models.Model):
    _name = "b2b.file"
    _description = "B2B File"
    name=fields.Char(string="Nama File")
    ext=fields.Char(string="Extension")
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('open', 'Open'),
                    ('done', 'Done'),
                    ('pmp', 'PMP'),
                    ('error', 'Error'),
                    ],string='Status',default='open')
    date=fields.Date(string="Tanggal Upload")

    @api.multi
    def insert_error_monitoring(self,type,file=None,obj=None,additional=None,qty1=None,qty2=None,lot=None,old_line=None,new_line=None,lot_id=None,sl=None):
        old_line_ids = []
        new_line_ids = []
        if old_line and new_line:
            nomor = 0
            for ress in old_line:  
                nomor = nomor+1
                old_line_ids.append([0,False,{
                        'nomor':nomor,
                        'name':ress.name,
                        'b2b_file_id':ress.b2b_file_id,
                    }])
            nomor = 0
            for res in new_line:
                nomor = nomor+1
                new_line_ids.append([0,False,{
                        'name':res,
                        'nomor':nomor,
                    }])
        # if sl:
        #     old_line = []
        #     for line in sl:
        #         import ipdb; ipdb.set_trace()
        #         line_data = {
        #             'kode_md_pembuka_po':line.kode_md_pembuka_po,
        #             'kode_md_qq':line.kode_md_qq,
        #             'kode_type':line.kode_md_pembuka_po,
        #             'no_ship_list':line.kode_md_pembuka_po,
        #             'kode_md':line.kode_md_pembuka_po,
        #             'no_rangka':line.kode_md_pembuka_po,
        #             'no_mesin':line.kode_md_pembuka_po,
        #             'no_sipb':line.kode_md_pembuka_po,
        #             'tgl_ship_list':line.kode_md_pembuka_po,
        #             'nopol_expedisi':line.kode_md_pembuka_po,
        #             'kode_warna':line.kode_md_pembuka_po
        #         }
        #         if line_data in old_line:
        #             new_line_ids.append([0,False,line_data])
        #         else:
        #             old_line.append(line_data)
        #             old_line_ids.append([0,False,line_data])

        keterangan = ""
        lot_data = ""
        if file:
            base_file, ext = os.path.splitext(file)
            ext_fix = ext.replace('.', '')
            name = os.path.basename(file)
        elif obj:
            ext_fix = obj.ext if 'ext' in obj else ""
            name = obj.name if 'name' in obj else obj.id
        if type == 'gagal_import':
            keterangan = "Gagal Import file. " + str(additional) 
        elif type == 'sudah_ada':
            keterangan = "Nama File Duplikat(sudah ada di b2b.file)"
        elif type == 'sudah_ada_archin':
            keterangan = "Nama File Duplikat(sudah ada di folder archin)"
        elif type == 'len_inv_sl':
            ext_fix = 'INV'
            keterangan = "Proses Pembuatan Invoice Gagal. " + str(additional) +" (ID inv_line)"
        elif type == 'len_fdo_ps':
            ext_fix = 'FDO'
            keterangan = "Proses Pembuatan Invoice Gagal. " + str(additional) +" (ID fdo_line)"
        elif type == 'lot_exists':
            keterangan = "Gagal Membuat lot karena lot sudah ada."
            ext_fix = 'INV'
            lot_data = lot
        elif type == 'account_invoice_exists':
            ext_fix = 'INV'
            keterangan = "Proses Pembuatan Invoice Gagal. Invoice Sudah Ada. (ID inv_line)"
        # if monitoring do exist, add total_check
        monitoring = self.env['b2b.file.monitoring'].search([('name','=',name),('ext','=',ext_fix)])
        if not monitoring:
            b2b_file = {
                'name': name,
                'ext' : ext_fix,
                'keterangan': keterangan,
                'date' : time.strftime('%Y-%m-%d %H:%M:%S'),
                'qty_1': qty1,
                'qty_2': qty2,
                'type': type,
                'lot_data': lot_data,                                                             
                'lot_id': lot_id,                                                             
                'old_line_ids': old_line_ids,                                                                
                'new_line_ids': new_line_ids,                                                                
                }
            self.env['b2b.file.monitoring'].create(b2b_file)
        else:
            monitoring.old_line_ids = False
            monitoring.new_line_ids = False
            monitoring.write({
                'keterangan' : keterangan,
                'last_check' : time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_check' : int(monitoring.total_check)+1, 
                'type': type,
                'qty_1': qty1,
                'qty_2': qty2,
                'lot_data': lot_data,
                'lot_id': lot_id,                                                        
                'old_line_ids': old_line_ids,                                                                
                'new_line_ids': new_line_ids,   
            })
    
    @api.multi
    def configuration_file(self):
        configuration_file = {}
        obj_config=self.env['b2b.configuration.folder'].search([('active','=',True)])
        configuration_file.update({
                            'folder_in':obj_config.folder_in,
                            'folder_proses':obj_config.folder_proses,
                            'folder_archin': obj_config.folder_archin,
                            'folder_error': obj_config.folder_error,
                            #'folder_error': "'"+obj_config.folder_eror+"'",
                             }) 
        return configuration_file
    
    @api.multi
    def check_file_in_in(self):
        folder = self.configuration_file()
        for file in os.listdir(folder['folder_in']) :
               folder_in_file=os.path.join(folder['folder_in'],file)
               if os.access(folder_in_file, os.W_OK) :
                   os.rename(folder_in_file,os.path.join(folder['folder_proses'],file))
        return True
       
    @api.multi            
    def do_import(self,file):
        base_file, ext = os.path.splitext(file)
        ext_fix = ext.replace('.', '')
        try:
            any_file_in_proses = open(file, 'r')
            ct = any_file_in_proses.read().splitlines()
            obj_cek_file=self.search([
                                      ('name','=', os.path.basename(file)),
                                      ('ext','=', ext),
                                      ])
                                    #   ('ext','=', ext_fix),
                                    #   ], limit = 1)
            # if obj_cek_file and ext_fix != 'PS':
            #     raise exceptions.Warning('File import sudah ada!')
            # else:
            if not obj_cek_file:
                b2b_file = {
                            'name': os.path.basename(file),
                            'ext' :ext_fix, 
                            'state' :'open',         
                            'date' :time.strftime('%Y-%m-%d %H:%M:%S'),                                                                                                
                            }
                b2b_file_id =self.create(b2b_file)
                for n in ct:
                    b2b_file_content = {
                            'name': n,        
                            'b2b_file_id' :b2b_file_id.id,                                                                                                
                            }
                    obj_file_content = self.env['b2b.file.content'].create(b2b_file_content)
        except Exception as err:
            # file_content = self.env['b2b.file.content'].search([('b2b_file_id','=',obj_cek_file.id)])
            # self.insert_error_monitoring('sudah_ada',file,additional=err,old_line=file_content,new_line=ct)
            #TODO SEND EMAIL ERROR
            return False
        return True
          
    @api.multi
    def read_file(self):
        folder = self.configuration_file()
        error=""
        check=True
        if not os.path.exists(folder['folder_proses']) :
            error += 'Folder '+folder['folder_proses']+' Tidak Ditemukan '+os.linesep
            check=False
        if not os.path.isdir(folder['folder_proses']) :
            error += 'Folder '+folder['folder_proses']+' Bukan Folder '+os.linesep
            check=False
        if not os.path.exists(folder['folder_in']):   
            error += 'Folder '+folder['folder_in']+' Tidak Ditemukan '+os.linesep
            check=False
        if not os.path.isdir(folder['folder_in']) :
            error += 'Folder '+folder['folder_proses']+' Bukan Folder '+os.linesep
            check=False
        if not os.path.exists(folder['folder_archin']):  
            error += 'Folder '+folder['folder_archin']+' Tidak Ditemukan '+os.linesep
            check=False
        if not os.path.isdir(folder['folder_archin']) :
            error += 'Folder '+folder['folder_proses']+' Bukan Folder '+os.linesep
            check=False
        if not os.path.exists(folder['folder_error']):  
            error += 'Folder '+folder['folder_error']+' Tidak Ditemukan '+os.linesep
            check=False
        if not os.path.isdir(folder['folder_error']) :
            error += 'Folder '+folder['folder_error']+' Bukan Folder '+os.linesep
            check=False
        if not os.access(folder['folder_proses'], os.W_OK) :
            error += 'Folder '+folder['folder_proses']+' Tidak Mempunyai Hak Akses Tulis '+os.linesep
            check=False
        if not os.access(folder['folder_in'], os.W_OK) :
            error += 'Folder '+folder['folder_in']+' Tidak Mempunyai Hak Akses Tulis '+os.linesep
            check=False
        if not os.access(folder['folder_error'], os.W_OK) :
            error += 'Folder '+folder['folder_error']+' Tidak Mempunyai Hak Akses Tulis '+os.linesep
            check=False
        if not os.access(folder['folder_archin'], os.W_OK) :
            error += 'Folder '+folder['folder_archin']+' Tidak Mempunyai Hak Akses Tulis '+os.linesep
        if not check :
            self.send_mail(error)
        else :
            self.check_file_in_proses(folder)
      
    @api.multi
    def check_file_in_proses(self,folder):
        files=self.getfiles(folder['folder_proses'])
        res=True
        # import ipdb
        # ipdb.set_trace()
        for file in files :
            if not self.do_import(file) :
                os.rename(file, os.path.join(folder['folder_error'],os.path.basename(file)))
                res=False
                break
        if res :
            for file in files :
                os.rename(file, os.path.join(folder['folder_archin'],os.path.basename(file)))
        else :
            raise osv.except_osv(('Perhatian !'), ('xxx')) 
                # file_in_process = os.path.exists(os.path.join(folder['folder_archin'],os.path.basename(file)))
                # base_file, ext = os.path.splitext(file)
                # now = datetime.now()
                # if not file_in_process:
                #     os.rename(file, os.path.join(folder['folder_archin'],os.path.basename(file)))
                # else:
                #     self.insert_error_monitoring('sudah_ada_archin',file, )
                #     if ext == '.PS':
                #         os.rename(file, os.path.join(folder['folder_archin'],(str(os.path.basename(file))+"_"+str(now.year))))
                #     else:
                #         os.rename(file, os.path.join(folder['folder_error'],os.path.basename(file)))
        
            
       
    def getfiles(self,dirpath):
        # import ipdb; ipdb.set_trace()
        a = [os.path.join(dirpath, s) for s in os.listdir(dirpath)
             if os.path.isfile(os.path.join(dirpath, s))] 
        if len(a) == 0 :
            self.check_file_in_in()
            a = [os.path.join(dirpath, s) for s in os.listdir(dirpath)
             if os.path.isfile(os.path.join(dirpath, s))]
        a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
        return a


# ------------------------>>> PROSES <<----------------------------------------
    @api.multi
    def proses(self):
        obj_inv_header=self.env['b2b.file.inv.header'].search([('state','=','draft')],limit=1)
        if obj_inv_header :
            obj_inv=self.env['b2b.file.inv.header'].check_proses(obj_inv_header)
        else :
            obj_inv_header_error=self.env['b2b.file.inv.header'].search([('state','=','error')])
            if obj_inv_header_error :
                obj_inv_header_error.write({'state':'draft'})
                
                
    @api.multi
    def proses_sparepart(self):
        obj_fdo_header=self.env['b2b.file.fdo.header'].search([('state','=','draft')],limit=1)
        if obj_fdo_header :
            obj_fdo=self.env['b2b.file.fdo.header'].check_proses_sparepart(obj_fdo_header)
        else :
            obj_fdo_header_error=self.env['b2b.file.fdo.header'].search([('state','=','error')])
            if obj_fdo_header_error :
                obj_fdo_header_error.write({'state':'draft'})
            
            

    def send_mail(self, cr, uid, ids ,error,context=None):
        res_id = self.read(cr, uid, ids, context)[0]['id']
        val = self.browse(cr, uid, ids, context={})[0]
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        email_obj = self.pool.get('email.template')   
        template_ids = email_obj.search(cr, uid, [('name', '=', 'Test')])  
        email = email_obj.browse(cr, uid, template_ids[0]) 
        email_obj.write(cr, uid, template_ids, {'email_from': email.email_from,
                                                'email_to': email.email_to,
                                                'subject': email.subject,  
                                                'body_html': error})
        
        search_mail=self.pool.get('b2b.file.error.mail').search(cr,uid,[('name','=',error),
                                                                 ('model_id','=',obj_model_id[0]),
                                                                 ('transaction_id','=',val.id),], limit=1)
        
        if search_mail :
            mail_check=self.pool.get('b2b.file.error.mail').browse(cr,uid,search_mail)
            now=time.strftime('%Y-%m-%d %H:%M:%S')
            
            data=abs((datetime.strptime(now,"%Y-%m-%d %H:%M:%S")- datetime.strptime(mail_check.tanggal_kirim,"%Y-%m-%d %H:%M:%S")).seconds)
            jam=float(data)/3600
            
            if mail_check and jam > 3 :
                send=email_obj.send_mail(cr, uid, template_ids[0], res_id, True, context=context)
                if send :
                    error_id={
                              'name':error,
                              'tanggal_kirim':time.strftime('%Y-%m-%d %H:%M:%S'),
                              'model_id':obj_model_id[0],
                              'transaction_id':val.id
                              }
                    var_error =self.pool.get('b2b.file.error.mail').create(cr,uid,error_id,context=None)
        else :
            send=email_obj.send_mail(cr, uid, template_ids[0], res_id, True, context=context)
            if send :
                error_id={
                          'name':error,
                          'tanggal_kirim':time.strftime('%Y-%m-%d %H:%M:%S'),
                          'model_id':obj_model_id[0],
                          'transaction_id':val.id
                          }
                var_error =self.pool.get('b2b.file.error.mail').create(cr,uid,error_id,context=None)
            
        
# ------------------------>>> CHECK FILE <<----------------------------------------
    @api.multi
    def check_file(self):
        object_file=self.search([('state','=','open')], limit = 1)
        if not object_file:
            object_file_error=self.search([('state','=','error')])
            if object_file_error :
                object_file_error.write({'state':'open'})

        res= False
        if object_file :
            if object_file.ext == 'INV' :
                res=self.env['b2b.file.inv.header'].action_import(object_file)
            elif object_file.ext == 'SL' :
                res=self.env['b2b.file.sl'].action_import(object_file)           
            elif object_file.ext == 'PTRAC' :
                res=self.env['b2b.file.ptrac'].action_import(object_file)          
            elif object_file.ext == 'PSL' :
                res=self.env['b2b.file.psl'].action_import(object_file)
            elif object_file.ext == 'SIPB' :
                res=self.env['b2b.file.sipb'].action_import(object_file)
            elif object_file.ext == 'FM' :
                res=self.env['b2b.file.fm'].action_import(object_file)
            elif object_file.ext == 'FDO' :
                res=self.env['b2b.file.fdo.header'].action_import(object_file)
            elif object_file.ext == 'PS' :
                res=self.env['b2b.file.ps'].action_import(object_file)
            elif object_file.ext == 'PMP' :
                object_file.write({'state':'pmp'})
            else :
                object_file.write({'state':'done'})
            if res :
                object_file.write({'state':'done'})
                
    @api.multi
    def check_file_pmp(self):
        object_file=self.search([('ext','=','PMP'),('state','=','pmp')], limit=1)
        res= False
        if object_file :
            res=self.env['b2b.file.sparepart.pmp'].action_import(object_file)
            if res:
                object_file.write({'state':'done'})
    
    @api.multi
    def check_ps_status(self):
        self.env['b2b.file.ps'].check_status_ps_transfer()

class b2b_file_content(models.Model):
    _name = "b2b.file.content"
    _description = "B2B File Content"
    
    name=fields.Char(string="Isi Content")
    b2b_file_id=fields.Many2one('b2b.file',string="B2b File")
    
    
class b2b_file_sipb(models.Model):
    _name= "b2b.file.sipb"
    _description= "B2B File SIPB"
    
    no_sipb=fields.Char(string="No SIPB",size=25)
    tgl_sipb=fields.Date(string="Tanggal SIPB")
    no_spes=fields.Char(string="Sale Order",size=30)
    tgl_so=fields.Date(string="Tanggal SO")
    kode_type=fields.Char(string="Kode Type",size=3)
    kode_warna=fields.Char(string="Kode Warna",size=2)
    jumlah=fields.Float(string="Qty Motor")
    harga=fields.Float(string="Unit Price")
    discount=fields.Float(string="Disc For All Item")
    quotation_flag=fields.Char(string="Quotation Flag")
    no_po_md=fields.Char(string="No. PO MD",size=30)
    dealer_qq=fields.Char(string="Dealer QQ",size=10)
    amount_total=fields.Float(string="Amount Total")
    ppn_total=fields.Float(string="PPN Total")
    pph_total=fields.Float(string="PPN Total")
    

    @api.multi
    def action_import(self,file_obj):
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        try :
            for x in object_file_content :
                line = x.name.split(';')
                tgl_sipb=line[1][4:]+"-"+line[1][2:4]+"-"+line[1][0:2]
                tgl_so=line[3][4:]+"-"+line[3][2:4]+"-"+line[3][0:2]
                
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
                sipb_cek = self.search([
                        ('no_sipb','=', line[0]),
                        ('tgl_sipb','=', tgl_sipb),
                        ('no_spes','=', line[2]),
                        ('tgl_so','=', tgl_so),
                        ('kode_type','=', line[4]),
                        ('kode_warna','=', line[5]), 
                        ('jumlah','=', line[6]),
                        ('harga','=', line[7]),
                        ('discount','=', line[8]),
                        ('quotation_flag','=', line[9]),
                        ('no_po_md','=', line[10]), 
                        ('dealer_qq','=', line[11]),
                        ('amount_total','=', line[12]),
                        ('ppn_total','=', line[13]),
                        ('pph_total','=', line[14],                    ) 
                    ], limit = 1)
                if sipb_cek:
                    raise exceptions.Warning('SIPB di skip karena sudah ada di b2b.file.sipb dgn id %s!' %(sipb_cek.id))
                else:
                    sipb_id=self.create(sipb)
        except Exception as err:
            self._cr.rollback()
            if 'SIPB di skip karena sudah ada di b2b.file.sipb dgn id' in err:
                file_obj.write({
                    'state' : 'duplicate'
                })
            else:
                file_obj.write({
                    'state' : 'error'
                })
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            res=False
        finally :
            self._cr.commit()
        return res
class b2b_file_inv_header(models.Model):
    _name= "b2b.file.inv.header"
    _description= "B2B File INV Header"
     
    no_faktur=fields.Char(string="No Invoice",size=25)
    tgl_faktur=fields.Date(string="Tanggal Faktur")
    top=fields.Date(string="TOP")
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('open', 'Open'),
                    ('done', 'Done'),
                    ('error', 'Error')
                    ],string='Status',default='draft')
    top_ppn=fields.Date(string="TOP PPN")
    top_pph=fields.Date(string="TOP PPH")
    total_invoice=fields.Float(string="Total Invoice")
    ppn_total=fields.Float(string="PPN Total")
    pph_total=fields.Float(string="PPN Total")
    b2b_file_inv_line=fields.One2many('b2b.file.inv.line','b2b_file_inv_header_id',string="B2B File Inv Line")
    
    @api.multi
    def action_import(self,file_obj):
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        purchase_line=False
        try :
            line = object_file_content[0].name.split(';')
            tgl_faktur=line[1][4:]+"-"+line[1][2:4]+"-"+line[1][0:2]
            top=line[2][4:]+"-"+line[2][2:4]+"-"+line[2][0:2]
            top_ppn=line[3][4:]+"-"+line[3][2:4]+"-"+line[3][0:2]
            top_pph=line[4][4:]+"-"+line[4][2:4]+"-"+line[4][0:2]
            
            obj_cek_line_header=self.search([
                                             ('no_faktur','=', line[0]),
                                             ('tgl_faktur','=', tgl_faktur),
                                             ('top','=', top),
                                             ('top_ppn','=', top_ppn),
                                             ('top_pph','=', top_pph),
                                             ('total_invoice','=', line[16]),
                                             ('ppn_total','=', line[17]),
                                             ('pph_total','=', line[18]),
                                             ])
            if obj_cek_line_header:
                raise exceptions.Warning('Invoice header sudah ada di b2b.file.inv.header!')
            elif not obj_cek_line_header :
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
                inv_header_id=self.create(inv_header)
                print 'XXXXXXXXXXXXX> Create INV Header ',inv_header_id
                for x in object_file_content :
                    line = x.name.split(';')
                    
                    obj_sipb=self.env['b2b.file.sipb'].search([('no_sipb','=',line[6]),
                                                              ('kode_type','=',line[7]),
                                                              ('kode_warna','=',line[8]),
                                                              ])
                    #TODO UBAH MENJADI QUERY
                    obj_warna=self.env['product.attribute.value'].search([('code','=',line[8])]) 
                    obj_product=self.env['product.product'].search([('name','=',line[7]),('attribute_value_ids','=',obj_warna.id)])
                    if not obj_product :
                        obj_product=self.env['product.product'].search([('name','=',line[7])], limit = 1)
                    
                    if obj_product:
                        product_id = obj_product.id
                    else:
                        raise exceptions.Warning('Product %s tidak ditemukan!' %(line[7]))
                    
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
                    inv_line = self.env['b2b.file.inv.line'].search([
                        ('no_ship_list','=', line[5]), 
                        ('purchase_order_line_id','=',purchase_line),
                        ('no_sipb','=', line[6]),
                        ('kode_type','=', line[7]),
                        ('kode_warna','=', line[8]),
                        ('qty','=', line[9]),
                        ('amount','=', line[10]), 
                        ('ppn','=', line[11]),
                        ('pph','=', line[12]),
                        ('discount_quotation','=', line[13]),
                        ('discount_type_cash','=', line[14]),
                        ('discount_other','=', line[15]),
                    ])
                    if inv_line:
                        raise exceptions.Warning('Invoice line sudah ada pada b2b.file.inv.line!')
                    inv_header_line_id=self.env['b2b.file.inv.line'].create(inv_header_line)
                    print 'XXXXXXXXXXXX> INV Line', inv_header_line_id
        except Exception as err:
            self._cr.rollback()
            if 'Invoice line sudah ada pada b2b.file.inv.line!' in err or 'Invoice header sudah ada di b2b.file.inv.header!' in err:
                file_obj.write({
                    'state' : 'duplicate'
                })
            else:
                file_obj.write({
                    'state' : 'error'
                })
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            print 'XXXXXXXXX> Err ',err
            print 'XXXXXXXXX> Err ID ',line
            res=False
        finally :
            self._cr.commit()
        return res
    
    def _get_journal_id(self, cr, uid, ids, branch_id,context=None):
        set_account_journal = {}
        obj_account = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id),])
        jornal=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account)
        journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_unit_id.id
        account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_unit_id.default_credit_account_id.id
        set_account_journal.update({'journal_id':journal_id,'account_id': account_id, })
        return set_account_journal

    @api.multi
    def check_proses(self,obj_inv_header,context=None):
        check = []
        obj_pph=self.env['account.tax'].search([('name','ilike','PPh 22')])
        for x in obj_inv_header :
            discount_cash=0.00
            discount_program=0.00
            discount_lain=0.00
            err_id = ""
            for i in x.b2b_file_inv_line :
                discount_cash +=i.discount_type_cash
                discount_program +=i.discount_quotation 
                discount_lain +=i.discount_other
                obj_sl=self.env['b2b.file.sl'].search([('no_sipb','=',i.no_sipb),
                                                    ('kode_type','=',i.kode_type),
                                                    ('kode_warna','=',i.kode_warna),
                                                    ('no_ship_list','=',i.no_ship_list)], order='id ASC')
                
                
                
                obj_sipb=self.env['b2b.file.sipb'].search([('no_sipb','=',i.no_sipb),
                                                            ('kode_type','=',i.kode_type),
                                                            ('kode_warna','=',i.kode_warna),
                                                            ])

                total=len(obj_sl)
                if  total == i.qty and  obj_sipb:
                    check.append(True)
                    # print ">>>>>>>>>>>>>>>>.BENAR",i.id
                else :
                    # import ipdb; ipdb.set_trace()
                    err_id += str(i.id)+","
                    # print ">>>>>>>>>>>>>>>>.SALAH",i.id
                    x.write({'state':'error'})
                    # Insert Monitoring
                    add = "Terdapat selisih antara Invoice dan SL"
                    if not obj_sipb:
                        add = "SIPB blm ada!"
                    if total/i.qty == 2:
                        add = "SL double"
                    self.env['b2b.file'].insert_error_monitoring('len_inv_sl',obj=i,additional = add,qty1=i.qty,qty2=total,sl = obj_sl)
                    check.append(False)
            print ">>>>>>>>>>>>>>>>.SALAH",err_id
            if all(check):
                obj_branch=self.env['wtc.branch'].search([('branch_type','=','MD')], limit=1)
                obj_location=self.env['stock.picking.type'].search([('branch_id','=',obj_branch.id),('code','=','incoming')])[0]
                account_and_journal = self._get_journal_id(obj_branch.id)
                
                ######-----BUAT INVOICE HEADER------####
                invoice = {
                    'origin': obj_sipb.no_po_md,
                    'name': obj_sipb.no_po_md,
                    'branch_id':obj_branch.id,
                    'division':'Unit',
                    'partner_id':obj_branch.default_supplier_id.id,
                    'date_invoice':time.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_due':x.top,
                    'payment_term':False,
                    'document_date':x.tgl_faktur ,
                    'journal_id':account_and_journal['journal_id'],
                    'account_id':account_and_journal['account_id'],
                    'consolidated':True,
                    'supplier_invoice_number':x.no_faktur,
                    'discount_cash':discount_cash,
                    'discount_program':discount_program,
                    'discount_lain':discount_lain,
                    'pajak_gabungan':True,
                    #'amount_untaxed':amount_untaxed,
                    #'amount_tax':x.ppn_total,
                    #'amount_total':x.total_invoice,
                    'type': 'in_invoice',
                    'transaction_id':-1,
                }
                invoices = self.env['account.invoice'].search([
                    ('origin','=',obj_sipb.no_po_md),
                    ('name','=',obj_sipb.no_po_md),
                    ('branch_id','=',obj_branch.id),
                    ('division','=','Unit'),
                    ('document_date','=',x.tgl_faktur),
                    ('supplier_invoice_number','=',x.no_faktur),
                    ('type','=','in_invoice'),
                    ('discount_cash','=',discount_cash),
                    ('discount_program','=',discount_program),
                    ('discount_lain','=',discount_lain),
                    ('journal_id','=',account_and_journal['journal_id']),
                    ('account_id','=',account_and_journal['account_id']),
                ])
                if invoices:
                    self.env['b2b.file'].insert_error_monitoring('account_invoice_exists',obj=i)
                    x.write({'state':'error'})
                else:
                    invoice_id=self.env['account.invoice'].create(invoice)
                    print ">>>>>>>>> Acount Invoice ",invoice_id.name
                    x.write({'state':'done'})
                
                    ######-----BUAT INVOICE LINE------####
                    for line_inv in x.b2b_file_inv_line : 
                        obj_warna=self.env['product.attribute.value'].search([('code','=',line_inv.kode_warna)])   
                        obj_product=self.env['product.product'].search([('name','=',line_inv.kode_type),('attribute_value_ids','=',obj_warna.id)])
                        if not obj_product :
                            obj_product=self.env['product.product'].search([('name','=',line_inv.kode_type)], limit = 1)
                        if obj_product.property_stock_account_input :
                            account_id = obj_product.property_stock_account_input.id
                        elif obj_product.categ_id.property_stock_account_input_categ :
                            account_id = obj_product.categ_id.property_stock_account_input_categ.id
                        elif obj_product.categ_id.parent_id.property_stock_account_input_categ :
                            account_id = obj_product.categ_id.parent_id.property_stock_account_input_categ.id
                        invoice_line = {
                            'name':[str(name) for id, name in obj_product.name_get()][0],
                            'product_id':obj_product.id,
                            'quantity':line_inv.qty,
                            'price_unit':(line_inv.amount+line_inv.ppn+(line_inv.discount_type_cash+line_inv.discount_other+line_inv.discount_quotation)*1.1)/line_inv.qty,
                            'invoice_id':invoice_id.id,
                            'invoice_line_tax_id': [(6,0,[obj_product.supplier_taxes_id.id,obj_pph.id])] ,
                            'account_id': account_id,
                            'purchase_line_id':line_inv.purchase_order_line_id,
                            'consolidated_qty':line_inv.qty,
                            #'force_cogs': force_cogs                 
                        }
                        invoice_line_id=self.env['account.invoice.line'].create(invoice_line)
                        obj_sl_ok=self.env['b2b.file.sl'].search([('no_sipb','=',line_inv.no_sipb),
                                                            ('kode_type','=',line_inv.kode_type),
                                                            ('kode_warna','=',line_inv.kode_warna),
                                                            ('no_ship_list','=',line_inv.no_ship_list)])
                        
                        for sl_ok in obj_sl_ok :
                            obj_sipb_lot=self.env['b2b.file.sipb'].search([('no_sipb','=',sl_ok.no_sipb),
                                                                ('kode_type','=',sl_ok.kode_type),
                                                                ('kode_warna','=',sl_ok.kode_warna),
                                                                ])
                            
                            obj_fm=self.env['b2b.file.fm'].search([('no_sipb','=',sl_ok.no_sipb),
                                                                ('kode_type','=',sl_ok.kode_type),
                                                                ('kode_warna','=',sl_ok.kode_warna),
                                                                ('no_mesin','=',sl_ok.no_mesin),
                                                                ('no_rangka','=',sl_ok.no_rangka),
                                                                ])
                            ######-----BUAT STOCK PRODUCTION LOT------####
                            obj_pucrhase_order=self.env['purchase.order'].search([('name','=',obj_sipb_lot.no_po_md)])
                            if not obj_pucrhase_order :
                                obj_pucrhase_order=self.env['purchase.order'].search([('origin','=',obj_sipb_lot.no_po_md)])
                                
                            update_lot={
                                'chassis_no' : str(sl_ok.no_rangka) if sl_ok.no_rangka else False, 
                                'name' : str(sl_ok.no_mesin) if sl_ok.no_mesin else False,
                                'branch_id':obj_branch.id,
                                'division' : 'Unit',
                                'product_id':obj_product.id,
                                'supplier_id':obj_branch.default_supplier_id.id,
                                'location_id' :obj_location.default_location_src_id.id,
                                'hpp' :(line_inv.amount+(line_inv.discount_type_cash+line_inv.discount_other+line_inv.discount_quotation))/line_inv.qty,
                                'purchase_order_id' :obj_pucrhase_order.id if  obj_pucrhase_order else False,
                                'no_sipb': str(sl_ok.no_sipb) if sl_ok.no_sipb else False,
                                'no_faktur': str(obj_fm.no_faktur) if obj_fm.no_faktur else False,
                                'no_ship_list': str(sl_ok.no_ship_list) if sl_ok.no_ship_list else False,
                                'tgl_ship_list':sl_ok.tgl_ship_list,
                                'state':'intransit',
                                'tahun': obj_fm.tahun_produksi,
                                'supplier_invoice_id': invoice_id.id
                                }
                            lot = self.env['stock.production.lot'].search([('name','=',sl_ok.no_mesin),('chassis_no','=',sl_ok.no_rangka)])
                            if not lot:
                                update_lot_id=self.env['stock.production.lot'].create(update_lot)
                            else:
                                self.env['b2b.file'].insert_error_monitoring('lot_exists',obj=i,lot=update_lot,lot_id=lot.id)
                    
                    invoice_id.button_reset_taxes()
                    workflow.trg_validate(self._uid, 'account.invoice', invoice_id.id, 'invoice_open', self._cr)

class b2b_file_inv_line(models.Model):
    _name= "b2b.file.inv.line"
    _description= "B2B File INV Line"
    
    b2b_file_inv_header_id=fields.Many2one('b2b.file.inv.header', ondelete='cascade')
    purchase_order_line_id=fields.Char(string="")
    no_ship_list=fields.Char(string="No. Ship List",size=19)
    no_sipb=fields.Char(string="No. SIPB",size=25)
    kode_type=fields.Char(string="Kode Type",size=3)
    kode_warna=fields.Char(string="Kode Warna",size=2)
    qty=fields.Float(string="Qty Motor")
    amount=fields.Float(string="Amount")
    ppn=fields.Float(string="PPN")
    pph=fields.Float(string="PPH")
    discount_quotation=fields.Float(string="Discount Quotation")
    discount_type_cash=fields.Float(string="Discount Cash")
    discount_other=fields.Float(string="Discount Other")
    

class b2b_file_sl(models.Model):
    _name= "b2b.file.sl"
    _description= "B2B File SL"
     
    no_mesin=fields.Char(string="No Mesin",size=16)
    no_rangka=fields.Char(string="No Rangka",size=17)
    kode_type=fields.Char(string="Kode Type",size=3)
    kode_warna=fields.Char(string="Kode Warna",size=2)
    kode_md=fields.Char(string="Kode MD",size=10)
    no_sipb=fields.Char(string="No. SIPB",size=25)
    no_ship_list=fields.Char(string="No. Ship List",size=19)
    tgl_ship_list=fields.Date(string="Tgl Ship List")
    nopol_expedisi=fields.Char(string="Nopol Expedisi",size=12)
    kode_md_qq=fields.Char(string="Kode MD QQ",size=10)
    kode_md_pembuka_po=fields.Char(string="Kode MD PO",size=10)
    nama_expedisi=fields.Char(string="Nama Expedisi")
    
    
    @api.multi
    def action_import(self,file_obj):
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        try :
            for x in object_file_content :
                line = x.name.split(';')
                no_mesin=line[0].replace(" ", "")
                tgl_ship_list=line[7][4:]+"-"+line[7][2:4]+"-"+line[7][0:2]
                obj_check_double=self.env['b2b.file.sl'].search([
                            ('no_mesin','=', no_mesin),
                            ('no_rangka','=',line[1]),
                            ('kode_type','=',line[2]),
                            ('kode_warna','=',line[3]),
                            ('kode_md','=',line[4]),
                            ('no_sipb','=', line[5]),
                            ('no_ship_list','=', line[6]),
                            ('tgl_ship_list','=', tgl_ship_list),
                            ('nopol_expedisi','=', line[8]),
                            ('kode_md_qq','=', line[9]),
                            ('kode_md_pembuka_po','=', line[10]),
                            ('nama_expedisi','=', line[13]),
                            ], limit = 1)
                if not obj_check_double :
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
                            'nama_expedisi': line[13],                        
                        }
                    sl_id=self.create(sl)
                elif obj_check_double :
                    raise exceptions.Warning('SL di skip karena sudah ada pada b2b.file.sl dgn id %s !' %(obj_check_double.id))
        except Exception as err:
            self._cr.rollback()
            if 'SL di skip karena sudah ada pada b2b.file.sl dgn id' in err:
                file_obj.write({
                    'state' : 'duplicate'
                })
            else:
                file_obj.write({
                    'state' : 'error'
                })
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            res=False
        finally :
            self._cr.commit()
        return res

class b2b_file_fm(models.Model):
    _name= "b2b.file.fm"
    _description= "B2B File FM"
    
    no_mesin=fields.Char(string="No Mesin",size=16)
    no_rangka=fields.Char(string="No Rangka",size=17)
    kode_type=fields.Char(string="Kode Type",size=3)
    kode_warna=fields.Char(string="Kode Warna",size=2)
    kode_md=fields.Char(string="Kode MD",size=10)
    no_faktur=fields.Char(string="No Invoice",size=25)
    tahun_produksi=fields.Char(string="Tahun Produksi",size=4)
    harga_faktur_stnk=fields.Float(string="Harga Faktur STNK")
    no_ppud=fields.Char(string="NO PPUD",size=50)
    nama_kapal=fields.Char(string="Nama Kapal",size=25)
    no_sipb=fields.Char(string="No. SIPB",size=25)
    no_ship_list=fields.Char(string="No. Ship List",size=19)
    tgl_ship_list=fields.Date(string="Tgl Ship List",size=8)
    nopol_expedisi=fields.Char(string="Nopol Expedisi",size=12)

    
    @api.multi
    def action_import(self,file_obj):
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        try :
            for x in object_file_content :
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
                    fm_id=self.create(fm)
                elif obj_check_double :
                    raise exceptions.Warning('FM dengan nomor engine %s sudah ada di b2b.file.fm!' %(no_mesin))
        except Exception as err:
            self._cr.rollback()
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            if 'sudah ada di b2b.file.fm!' in err:
                file_obj.write({
                    'state' : 'duplicate'
                })
            else:
                file_obj.write({
                    'state' : 'error'
                })
            res=False
        finally :
            self._cr.commit()
        return res
    

class b2b_file_fdo_header(models.Model):
    _name= "b2b.file.fdo.header"
    _description= "B2B File FDO Header"
     
    no_invoice=fields.Char(string="No Invoice")
    tanggal_invoice=fields.Date(string="Tanggal Invoice")
    kode_md = fields.Char(string="Kode Main Dealer")
    top=fields.Date(string="TOP")
    b2b_file_fdo_line=fields.One2many('b2b.file.fdo.line','b2b_file_fdo_header_id',string="B2B File Fdo Line")
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('open', 'Open'),
                    ('done', 'Done'),
                    ('error', 'Error')
                    ],string='Status',default='draft')
    
    def _get_journal_id(self, cr, uid, ids, branch_id,context=None):
        set_account_journal = {}
        obj_account = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id),])
        jornal=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account)
        journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_sparepart_id.id
        account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_sparepart_id.default_credit_account_id.id
        set_account_journal.update({'journal_id':journal_id,'account_id': account_id, })
        return set_account_journal

    @api.multi
    def check_proses_sparepart(self,obj_fdo_header):
        check = []
       
        for x in obj_fdo_header :
            discount_lain=0.00
            kode_po = ''
#REKAP PS           
            # for i in x.b2b_file_fdo_line :
            #     discount_lain+=i.discount_satu
            #     obj_ps_rekap=self.env['b2b.file.rekap.ps'].search([('kode_ps','=',i.kode_ps),
            #                                                ('kode_sparepart','=',i.kode_sparepart), ])
                
            #     obj_fdo_qty=self.env['b2b.file.fdo.line'].search([('kode_ps','=',i.kode_ps),
            #                                                ('kode_sparepart','=',i.kode_sparepart),
            #                                                ('b2b_file_fdo_header_id','=',x.id),
            #                                                 ])
                

                
            #     obj_ps=self.env['b2b.file.ps'].search([('kode_ps','=',i.kode_ps),
            #                                                ('kode_sparepart','=',i.kode_sparepart), ])
            #     qty_all_fdo=0
            #     for fdo_line_qty in obj_fdo_qty :
            #         qty_all_fdo+=fdo_line_qty.qty

                

            #     for line_ps in obj_ps :
            #         if kode_po == '':
            #             kode_po = line_ps.kode_po_md
                        
           
                        
            #     qty_inv=obj_ps_rekap.qty_invoices+qty_all_fdo
            #     if obj_ps_rekap and  qty_inv <=  obj_ps_rekap.qty_ps:
            #         check.append(True)
            #         obj_ps_rekap.write({'qty_invoices':qty_inv})
            #         #print ">>>>>>>>>>>>>>>>.BENAR",i.id
            #     else :
            #         check.append(False)
            #         self.env['b2b.file.fdo.header'].browse(x.id).write({'state':'error'})
            #         #print ">>>>>>>>>>>>>>>>.SALAH",i.id
#REKAP PS
            err_id = ""
            for i in x.b2b_file_fdo_line :
                discount_lain+=i.discount_satu
                obj_ps=self.env['b2b.file.ps'].search([('kode_ps','=',i.kode_ps),
                                                           ('kode_sparepart','=',i.kode_sparepart), ])
                
                obj_fdo_qty=self.env['b2b.file.fdo.line'].search([('kode_ps','=',i.kode_ps),
                                                           ('kode_sparepart','=',i.kode_sparepart),
                                                           #('no_invoice','=',i.no_invoice),
                                                            ])
                qty_all_fdo=0
                for fdo_line_qty in obj_fdo_qty :
                    qty_all_fdo+=fdo_line_qty.qty
                qty_all_ps=0
                for line_ps in obj_ps :
                    qty_all_ps+= line_ps.qty_ps
                    if kode_po == '':
                        kode_po = line_ps.kode_po_md
                    
                if obj_ps and qty_all_ps == qty_all_fdo:
                    check.append(True)
                    # print ">>>>>>>>>>>>>>>>.BENAR",i.id,"QTY FDO=",qty_all_fdo,"QTY PS=",qty_all_ps
                else :
                    check.append(False)
                    self.env['b2b.file.fdo.header'].browse(x.id).write({'state':'error'})
                    err_id += str(i.id)+","
                    # print ">>>>>>>>>>>>>>>>.salah",i.id,"QTY FDO=",qty_all_fdo,"QTY PS=",qty_all_ps
                    self.env['b2b.file'].insert_error_monitoring('len_fdo_ps',obj=i,additional = 'Terdapat selisih antara FDO dan PS',qty1=qty_all_fdo,qty2=qty_all_ps)
            print ">>>>>>>>>>>>>>>>.SALAH",err_id
            if all(check):
                 
                obj_branch=self.env['wtc.branch'].search([('ahm_code','=',x.kode_md)])
                account_and_journal = self._get_journal_id(obj_branch.id)
                invoice = {
                         'origin': kode_po,
                         'name': kode_po or '/',
                         'branch_id':obj_branch.id,
                         'division':'Sparepart',
                         'partner_id':obj_branch.default_supplier_id.id,
                         'date_invoice':time.strftime('%Y-%m-%d %H:%M:%S'),
                         'document_date':x.tanggal_invoice ,
                         'journal_id':account_and_journal['journal_id'],
                         'account_id':account_and_journal['account_id'],
                         'consolidated':True,
                         'supplier_invoice_number':x.no_invoice,
                         'pajak_gabungan':True,
                         'date_due':x.top,
                         'payment_term':False,
                         #'discount_cash':discount_cash,
                         #'discount_program':discount_program,
                         'discount_lain':discount_lain,
                         #'amount_untaxed':amount_untaxed,
                         #'amount_tax':x.ppn_total,
                         #'amount_total':x.total_invoice,
                         'type': 'in_invoice',
                         'transaction_id':-1,                                        
                         }

                invoices = self.env['account.invoice'].search([
                    ('origin','=', kode_po),
                    ('name','=', kode_po or '/'),
                    ('branch_id','=',obj_branch.id),
                    ('division','=','Sparepart'),
                    ('partner_id','=',obj_branch.default_supplier_id.id),
                    ('document_date','=',x.tanggal_invoice ),
                    ('journal_id','=',account_and_journal['journal_id']),
                    ('account_id','=',account_and_journal['account_id']),
                    ('consolidated','=',True),
                    ('supplier_invoice_number','=',x.no_invoice),
                    ('pajak_gabungan','=',True),
                    ('date_due','=',x.top),
                    ('payment_term','=',False),
                    ('discount_lain','=',discount_lain),
                    ('type','=', 'in_invoice'),
                    ('transaction_id','=',-1),
                ])
                if invoices:
                    self.env['b2b.file'].insert_error_monitoring('account_invoice_exists',obj=i)
                    x.write({'state':'error'})
                else:
                    invoice_id=self.env['account.invoice'].create(invoice)
                    self.env['b2b.file.fdo.header'].browse(x.id).write({'state':'done'})
                    for line_inv in x.b2b_file_fdo_line :
                        account_id = False
                        obj_product=self.env['product.product'].search([('name','=',line_inv.kode_sparepart)])
                        if obj_product.categ_id.property_stock_account_input_categ :
                            account_id = obj_product.categ_id.property_stock_account_input_categ.id
                        elif obj_product.categ_id.parent_id.property_stock_account_input_categ :
                            account_id = obj_product.categ_id.parent_id.property_stock_account_input_categ.id
                        elif obj_product.property_stock_account_input :
                            account_id = obj_product.property_stock_account_input.id
                        invoice_line = {
                                        'name':obj_product.description or '/' ,
                                        'product_id':obj_product.id,
                                        'quantity':line_inv.qty,
                                        'price_unit':line_inv.price*1.1,
                                        'invoice_id':invoice_id.id,
                                        'invoice_line_tax_id': [(6,0,[obj_product.supplier_taxes_id.id])] ,
                                        'account_id': account_id,
                                        #'force_cogs': force_cogs                             
                                            }
                        invoice_line_id=self.env['account.invoice.line'].create(invoice_line)
                        lot_sparepart = {
                                    'no_invoice':line_inv.b2b_file_fdo_header_id.no_invoice,
                                    'tanggal_invoice':line_inv.b2b_file_fdo_header_id.tanggal_invoice,
                                    'kode_md':line_inv.b2b_file_fdo_header_id.kode_md,
                                    'top':line_inv.b2b_file_fdo_header_id.top,
                                    'kode_ps':line_inv.kode_ps,
                                    'kode_sparepart': line_inv.kode_sparepart ,
                                    'desc_sparepart':line_inv.desc_sparepart,
                                    'qty':line_inv.qty,
                                    'price':line_inv.price,
                                    'discount_satu':line_inv.discount_satu,  
                                    'discount_dua':line_inv.discount_dua,
                                    'discount_tiga':line_inv.discount_tiga,
                                    'dpp':line_inv.dpp,
                                    'kode_po_md':line_ps.kode_po_md,
                                    'ppn':line_inv.ppn,
                                    'top_ppn':line_inv.top_ppn,
                                    'discount_empat':line_inv.discount_empat,
                                    'invoice_jml':line_inv.invoice_jml,
                                    'seq':line_inv.seq,        
                                    }
                        lot_sparepart_id=self.env['b2b.file.lot.spareprt'].create(lot_sparepart)
                    invoice_id.button_reset_taxes()  
                    workflow.trg_validate(self._uid, 'account.invoice', invoice_id.id, 'invoice_open', self._cr)    
                    
                    self._cr.execute('''
                    SELECT kode_ps  FROM b2b_file_fdo_line
                    where b2b_file_fdo_header_id=%s
                    GROUP BY  kode_ps
                    ''',([x.id]))   
                    picks = self._cr.fetchall() 
                    
                    obj_location=self.env['stock.picking.type'].search([('branch_id','=',obj_branch.id),('code','=','incoming')])
                    
                    for line in picks:  
                        obj_purchase_order_inv=self.env['purchase.order'].search([('name','=',line_ps.kode_po_md)])
    
                        picking={
                            'picking_type_id': obj_location.id,
                            'branch_id':obj_branch.id,
                            'division' : 'Sparepart',
                            'partner_id':obj_branch.default_supplier_id.id,
                            'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                            'min_date':time.strftime('%Y-%m-%d %H:%M:%S'),
                            'start_date':obj_purchase_order_inv.start_date,
                            'end_date':obj_purchase_order_inv.end_date,
                            'origin':line[0],
                            'branch_id':obj_branch.id,
                            }     
                        picking_id=self.env['stock.picking'].create(picking)
                        obj_line_fdo=self.env['b2b.file.fdo.line'].search([('kode_ps','=',line[0]),('b2b_file_fdo_header_id','=',x.id)])
                        for y in obj_line_fdo :
                            ######-----BUAT STOCK MOVE------####
                            obj_product=self.env['product.product'].search([('name','=',y.kode_sparepart)])
                            move_line={
                                    'name': obj_product.description or '',
                                    'product_uom': obj_product.uom_id.id,
                                    'product_uos': obj_product.uom_id.id,
                                    'product_id':obj_product.id,
                                    'product_uom_qty': y.qty,
                                    'product_uos_qty': y.qty,
                                    'price_unit':y.price*1.1,
                                    'date': time.strftime('%Y-%m-%d'),
                                    'location_id':obj_location.default_location_src_id.id,
                                    'location_dest_id':obj_location.default_location_dest_id.id,
                                    'picking_id': picking_id.id,
                                    'picking_type_id': obj_location.id,
                                    'procurement_id': False,
                                    'origin':line[0],
                                    'branch_id': obj_branch.id,
                                    'categ_id': obj_product.categ_id.id,
                                    }
                            stock_move=self.env['stock.move'].create(move_line)
                        if picking_id:
                            picking_id.action_confirm()
                            picking_id.force_assign()
                        elif stock_move:
                            stock_move.action_confirm()
                            stock_move.force_assign()
                    
    @api.multi
    def action_import(self,file_obj):
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        try :
            for x in  object_file_content  :
                i = 0
                no_invoice = x.name[:i+25].strip()
                i+=25
                tanggal_invoice = x.name[i:i+8].strip()
                i+=8
                kode_md = x.name[i:i+5].strip()
                i+=5
                kode_ps = x.name[i:i+15].strip()
                i+=15
                kode_sparepart = x.name[i:i+25].strip()
                i+=25
                desc_sparepart = x.name[i:i+30].strip()
                i+=30
                qty = x.name[i:i+10]
                i+=10
                price = x.name[i:i+20]
                i+=20
                discount_satu = x.name[i:i+20]
                i+=20
                discount_dua = x.name[i:i+20]
                i+=20
                discount_tiga = x.name[i:i+20]
                i+=20
                dpp = x.name[i:i+20]
                i+=20
                top = x.name[i:i+8]
                i+=8
                ppn = x.name[i:i+20]
                i+=20
                top_ppn = x.name[i:i+8].strip()
                i+=8
                discount_empat = x.name[i:i+20]
                i+=20
                invoice_jml = x.name[i:i+20]
                i+=20
                zz = x.name[i:i+5].strip()
                i+=5
                seq = x.name[i:i+10] .strip()
                
                top_fix=top[4:]+"-"+top[2:4]+"-"+top[0:2]
                tanggal_invoice_fix=tanggal_invoice[4:]+"-"+tanggal_invoice[2:4]+"-"+tanggal_invoice[0:2]
                
                obj_check_header=self.env['b2b.file.fdo.header'].search([('no_invoice','=',no_invoice)])
                if not obj_check_header :
                    fdo = {
                            'no_invoice':no_invoice,
                            'kode_md':kode_md,
                            'tanggal_invoice' :tanggal_invoice_fix,
                            'top': top_fix,                  
                        }
                    fdo_id=self.env['b2b.file.fdo.header'].create(fdo)
                    top_ppn_fix=top_ppn[4:]+"-"+top_ppn[2:4]+"-"+top_ppn[0:2]
                fdo_line = {
                    'kode_md':kode_md,
                    'b2b_file_fdo_header_id':fdo_id.id,
                    'kode_ps':kode_ps,
                    'kode_sparepart' :kode_sparepart,
                    'desc_sparepart' : desc_sparepart, 
                    'qty' : qty,
                    'price' : price,
                    'discount_satu': discount_satu,
                    'discount_dua': discount_dua,
                    'discount_tiga': discount_tiga,
                    'dpp': dpp,
                    'ppn': ppn,       
                    'top_ppn': top_ppn_fix,
                    'discount_empat': discount_empat,
                    'invoice_jml': invoice_jml,
                    'zz': zz,
                    'seq':seq,                     
                }
                fdo_line_check = self.env['b2b.file.fdo.line'].search([
                    ('kode_ps','=',kode_ps),
                    ('kode_sparepart','=',kode_sparepart),
                    ('desc_sparepart','=',desc_sparepart), 
                    ('qty','=', qty),
                    ('price','=', price),
                    ('discount_satu','=', discount_satu),
                    ('discount_dua','=', discount_dua),
                    ('discount_tiga','=', discount_tiga),
                    ('dpp','=', dpp),
                    ('ppn','=', ppn), 
                    ('top_ppn','=', top_ppn_fix),
                    ('discount_empat','=', discount_empat),
                    ('invoice_jml','=', invoice_jml),
                    ('zz','=', zz),
                    ('seq','=',seq),
                ])
                if fdo_line_check:
                    raise exceptions.Warning('Terdapat duplikasi FDO line dengan id = %s .' %(fdo_line_check.id))
                fdo_line_id=self.env['b2b.file.fdo.line'].create(fdo_line)
        except Exception as err:
            self._cr.rollback()
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            res=False
        finally :
            self._cr.commit()
        return res
    
class b2b_file_fdo_line(models.Model):
    _name= "b2b.file.fdo.line"
    _description= "B2B File FDO Line"
    
    b2b_file_fdo_header_id=fields.Many2one('b2b.file.fdo.header', ondelete='cascade')
    kode_ps = fields.Char(string="Kode PS")
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    qty = fields.Float(string="Qty")
    price = fields.Float(string="Price")
    discount_satu = fields.Float(string="Discount 1")
    discount_dua = fields.Float(string="Discount 2")
    discount_tiga = fields.Float(string="Discount 3")
    dpp = fields.Float(string="DPP")
    ppn = fields.Float(string="DPP")
    top_ppn=fields.Date(string="TOP PPN")
    discount_empat = fields.Float(string="Discount 4")
    invoice_jml = fields.Float(string="Jumlah Invoice")
    zz = fields.Char(string="zz")
    seq=fields.Float(string="SEQ")
        

class b2b_file_rekap_ps(models.Model):
    _name= "b2b.file.rekap.ps"
    _description= "B2B File Rekap PS"
    
    kode_ps = fields.Char(string="Kode PS")
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    qty_ps = fields.Float(string="Qty PS")
    qty_invoices = fields.Float(string="Qty Invoices")
    
    
#     @api.multi
#     def action_check_ps(self):
#         self._cr.execute('''
#                  SELECT kode_ps,kode_sparepart  FROM b2b.file.ps
#                  where 1=1
#                  GROUP BY  kode_ps,kode_sparepart
#                  ''',([x.id]))   
#         picks = self._cr.fetchall() 
#         
#         for line in picks:  
            
        

class b2b_file_ps(models.Model):
    _name= "b2b.file.ps"
    _description= "B2B File PS"
     
    kode=fields.Char(string="Kode")
    kode_md = fields.Char(string="Kode MD")
    tanggal_ps=fields.Date(string="Tanggal PS")
    kode_ps = fields.Char(string="Kode PS")
    kode_po_md = fields.Char(string="Kode PO MD")
    type_po = fields.Char(string="Type PO")
    tgl_po = fields.Date(string="Tanggal XX")
    no_urut = fields.Char(string="One or Two")
    kode_dus = fields.Char(string="Kode Main Dealer")
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    qty_ps = fields.Float(string="Qty PS")
    qty_po = fields.Float(string="Qty PO")
    remaining_qty = fields.Float(string="Qty Remaining")
    status = fields.Selection([
                                ('packed at ahm','Packed at AHM'),
                                ('on intransit','On Intransit'),
                                ('received by md','Received by MD')
                            ], string="Status",default='packed at ahm')
    
   
           
    @api.multi
    def action_import(self,file_obj):
        print ">>>>>ssss"
        object_file_content=self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res =True
        try :
            for x in object_file_content :
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
                elif obj_ps_cek:
                    raise exceptions.Warning('PS sudah ada di b2b.file.ps!')
        except Exception as err:
            self._cr.rollback()
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            if 'PS sudah ada di b2b.file.ps' in err:
                file_obj.write({
                    'state' : 'duplicate'
                })
            else:
                file_obj.write({
                    'state' : 'error'
                })
            res=False
        finally :
            self._cr.commit()
        return res

    @api.multi
    def check_status_ps_transfer(self):
        object_file =self.search([('status','=','on intransit')])
        branch_id = self.env['wtc.branch'].search([('code','=','MML')])
        partner_id = self.env['res.partner'].search([('name','=','ASTRA HONDA MOTOR')])
        on_in_ship = self.env['stock.picking']
        

        for obj in object_file:
            # cek dulu datanya dapet atau tidak
            ois_src = on_in_ship.search([
                        ('origin','=',obj.kode_ps),
                        ('partner_id','=',partner_id.id),
                        ('branch_id','=',branch_id.id),
                        ('division','=','Sparepart'),
                        ('state','=','done'),
                    ])
            if ois_src:
                print "Data Berhasil didapat"
                print ois_src.id
                self.browse(obj.id).write({'status':'received by md'})
            else:
                print "Data tidak ada"

        
class b2b_file_lot_sparepart(models.Model):
    _name= "b2b.file.lot.spareprt"
    _description= "B2B File Lot Sparepart"
    
    no_invoice=fields.Char(string="No Invoice")
    kode_po_md=fields.Char(string="No PO MD")
    tanggal_invoice=fields.Date(string="Tanggal Invoice")
    kode_md = fields.Char(string="Kode Main Dealer")
    top=fields.Date(string="TOP")
    kode_ps = fields.Char(string="Kode PS")
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    qty = fields.Float(string="Qty")
    price = fields.Float(string="Price")
    discount_satu = fields.Float(string="Discount 1")
    discount_dua = fields.Float(string="Discount 2")
    discount_tiga = fields.Float(string="Discount 3")
    dpp = fields.Float(string="DPP")
    ppn = fields.Float(string="DPP")
    top_ppn=fields.Date(string="TOP PPN")
    discount_empat = fields.Float(string="Discount 4")
    invoice_jml = fields.Float(string="Jumlah Invoice")
    seq=fields.Float(string="SEQ")
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('open', 'Open'),
                    ('done', 'Done'),
                    ('error', 'Error')
                    ],string='Status',default='draft')


class b2b_sparepart_pmp(models.Model):
    _name= "b2b.file.sparepart.pmp"
    _description= "B2B File Sparepart PMP"     
    
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    het = fields.Float(string="HET")
    hpp = fields.Float(string="HPP")
    supplier = fields.Char(string="Supplier")
    sub_category = fields.Char(string="Sub Category")
    desc_sparepart_2 = fields.Char(string="Desc Sparepart 2")
    kolom_8=fields.Char(string="Kolom 8")
    kolom_9=fields.Char(string="Kolom 9")
    kolom_10=fields.Char(string="Kolom 10")
    kolom_11=fields.Char(string="Kolom 11")
    kolom_12=fields.Char(string="Kolom 12")
    kolom_13=fields.Char(string="Kolom 13")
    kolom_14=fields.Char(string="Kolom 14")
    kolom_15=fields.Char(string="Kolom 15")
    kolom_16=fields.Char(string="Kolom 16")
    kolom_17=fields.Char(string="Kolom 17")
    kolom_18=fields.Char(string="Kolom 18")
    kolom_19=fields.Char(string="Kolom 19")
    kolom_20=fields.Char(string="Kolom 20")        
    
    @api.multi
    def action_import(self,file_obj):
        object_file_content = self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id)])
        res = True
        try :
            for x in object_file_content :
                line = x.name.split(';')
                obj_sparepart=self.search([('kode_sparepart','=',line[0])])
                if not obj_sparepart:
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
                    pmp_id = self.create(pmp)
                else :
                    obj_sparepart.write({
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
                    })
                obj_product=self.env['product.template'].search([('name','=',line[0])]) 
                if line[5] == '' or line[5] == ' ':
                    line[5] = 'Sparepart'
                obj_product_category=self.env['product.category'].search([('name','=',line[5])]) 
                if not obj_product :
                    product_sparepart = {
                        'name': line[0],
                        'sale_ok': True,
                        'purchase_ok': True,
                        'type': 'product',
                        'list_price': line[2],
                        'description': line[6],
                        'default_code': line[1],
                        'active': True,
                        'cost_method': 'average',
                        'sale_delay': '7',
                        'categ_id': obj_product_category.id,
                        'valuation': 'real_time'
                    }
                    product_sparepart_id = self.env['product.template'].create(product_sparepart)
                    product_sparepart_id.write({'list_price':line[2]})
                else :
                    obj_product.write({
                        'name':line[0],
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
        except Exception:
            self._cr.rollback()
            res = False
        finally :
            self._cr.commit()
        return res
        
class b2b_file_error_main(models.Model):
    _name= "b2b.file.error.mail"
    _description= "B2B File Error Mail"
    _order = 'tanggal_kirim desc'
    
    name=fields.Char(string="Error")
    tanggal_kirim=fields.Datetime(string="Tanggal Send Mail")
    transaction_id = fields.Integer(string='Transaction Id')
    model_id = fields.Many2one('ir.model','Model')
    

class b2b_file_pmp_wizard(osv.osv_memory):
    _name= "b2b.file.pmp.wizard"

    def execute_pmp(self, cr, uid, ids, context=None):
        object_file=self.pool.get('b2b.file').check_file_pmp(cr,uid,ids,context=context)
        #self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Sparepart')                    
        # res= False
        # if object_file :
        #     res=self.env['b2b.file.sparepart.pmp'].action_import(object_file)
        #     if res:
        #         object_file.write({'state':'done'})

class b2b_file_ptrac_history(models.Model):
    _name = "b2b.file.ptrac.history"

    no_po_ahm = fields.Char(string='No PO AHM',size=35, required=True)
    part_no = fields.Char(string='Part No', size=30, required=True)
    qq_ship_to = fields.Char(string='QQ Ship To', size=10 )
    kode_md = fields.Char(string='Kode MD', size=10)
    kode_order = fields.Char(string='Kode Order', size=5)
    qty_po = fields.Float(string='Qty PO') 
    qty_shipping = fields.Float(string='Qty Shipping')
    month_deliver = fields.Date(string='Month Deliver') 
    no_po_md = fields.Char(string='No PO MD', size=35)
    qty_book = fields.Float(string='Qty Book') 
    qty_packing = fields.Float(string='Qty Packing') 
    qty_picking = fields.Float(string='Qty Picking') 
    dmodi = fields.Date(string='DMODI')
    dcrea = fields.Date(string='DCREA', required=True) 
    flag_fast_slow = fields.Char(string='Flag Fast Slow', size=1)
    qty_invoice = fields.Float(string='Qty Invoice') 
    flag_additional = fields.Char(string='Flag Additional', size=1)

class b2b_file_ptrac(models.Model):
    _name = "b2b.file.ptrac"

    no_po_ahm = fields.Char(string='No PO AHM',size=35, required=True)
    part_no = fields.Char(string='Part No', size=30, required=True)
    qq_ship_to = fields.Char(string='QQ Ship To', size=10 )
    kode_md = fields.Char(string='Kode MD', size=10)
    kode_order = fields.Char(string='Kode Order', size=5)
    qty_po = fields.Float(string='Qty PO') 
    qty_shipping = fields.Float(string='Qty Shipping')
    month_deliver = fields.Date(string='Month Deliver') 
    no_po_md = fields.Char(string='No PO MD', size=35)
    qty_book = fields.Float(string='Qty Book') 
    qty_packing = fields.Float(string='Qty Packing') 
    qty_picking = fields.Float(string='Qty Picking') 
    dmodi = fields.Date(string='DMODI')
    dcrea = fields.Date(string='DCREA', required=True) 
    flag_fast_slow = fields.Char(string='Flag Fast Slow', size=1)
    qty_invoice = fields.Float(string='Qty Invoice') 
    flag_additional = fields.Char(string='Flag Additional', size=1)
    
    @api.multi
    def action_import(self,file_obj):
        a = ''
        object_file_content = self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id),('name','!=',a)])
        print "Id file:",file_obj.id
        res = True
        try : 
            for obj in object_file_content:
                line = obj.name.split(';')

                month_deliver = line[7][0:4]+"-"+line[7][4:6]+"-"+line[7][6:8]
                dmodi = line[12][0:4]+"-"+line[12][4:6]+"-"+line[12][6:8]
                dcrea = line[13][0:4]+"-"+line[13][4:6]+"-"+line[13][6:8]

                ptrac_history = self.env['b2b.file.ptrac.history']
                ptrac_hs = {
                            'no_po_ahm':line[0],
                            'part_no': line[1],
                            'qq_ship_to': line[2],
                            'kode_md': line[3],
                            'kode_order': line[4],
                            'qty_po': line[5],
                            'qty_shipping': line[6],
                            'month_deliver': month_deliver,
                            'no_po_md': line[8],
                            'qty_book': line[9],
                            'qty_packing': line[10],
                            'qty_picking': line[11],
                            'dmodi':dmodi,
                            'dcrea': dcrea,
                            'flag_fast_slow': line[14],
                            'qty_invoice': line[15],
                            'flag_additional': line[16],                  
                        }
                ptrac_history.create(ptrac_hs)

                cek_ptrac = self.search([
                                            ('no_po_ahm','=',line[0]),
                                            ('part_no','=',line[1])
                                        ])
                if cek_ptrac:
                    print "PTRAC di Update"
                    ptrac_upd = self.browse(cek_ptrac.id).write({
                                                        'no_po_ahm':line[0],
                                                        'part_no': line[1],
                                                        'qq_ship_to': line[2],
                                                        'kode_md': line[3],
                                                        'kode_order': line[4],
                                                        'qty_po': line[5],
                                                        'qty_shipping': line[6],
                                                        'month_deliver': month_deliver,
                                                        'no_po_md': line[8],
                                                        'qty_book': line[9],
                                                        'qty_packing': line[10],
                                                        'qty_picking': line[11],
                                                        'dmodi':dmodi,
                                                        'dcrea': dcrea,
                                                        'flag_fast_slow': line[14],
                                                        'qty_invoice': line[15],
                                                        'flag_additional': line[16],
                                                    })
                    print ptrac_upd
                else:          
                    print "PTREC di Insert"    
                    ptrac = {
                                'no_po_ahm':line[0],
                                'part_no': line[1],
                                'qq_ship_to': line[2],
                                'kode_md': line[3],
                                'kode_order': line[4],
                                'qty_po': line[5],
                                'qty_shipping': line[6],
                                'month_deliver': month_deliver,
                                'no_po_md': line[8],
                                'qty_book': line[9],
                                'qty_packing': line[10],
                                'qty_picking': line[11],
                                'dmodi':dmodi,
                                'dcrea': dcrea,
                                'flag_fast_slow': line[14],
                                'qty_invoice': line[15],
                                'flag_additional': line[16],                  
                            }
                    print ptrac
                    ptrac_id=self.create(ptrac)
        except Exception :
            self._cr.rollback()
            res = False
        finally :
            self._cr.commit()
        return res

class b2b_file_psl(models.Model):
    _name = "b2b.file.psl"

    kode=fields.Char(string="Kode")
    kode_md = fields.Char(string="Kode MD")
    tanggal_psl =fields.Date(string="Tanggal PS")
    kode_psl = fields.Char(string="Kode PS")
    kode_po_md = fields.Char(string="Kode PO MD")
    type_po = fields.Char(string="Type PO")
    tgl_po = fields.Date(string="Tanggal XX")
    no_urut = fields.Char(string="One or Two")
    kode_dus = fields.Char(string="Kode Main Dealer")
    kode_sparepart = fields.Char(string="Kode Sparepart")
    desc_sparepart = fields.Char(string="Desc Sparepart")
    qty_psl = fields.Float(string="Qty PS")
    qty_po = fields.Float(string="Qty PO")
    remaining_qty = fields.Float(string="Qty Remaining")

    @api.multi
    def action_import(self,file_obj):
        a=''
        object_file_content = self.env['b2b.file.content'].search([('b2b_file_id','=',file_obj.id),('name','!=',a)])
        print "Id file:",file_obj.id
        res = True

        try :
            for obj in object_file_content :
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
                    for ids in src_ps:
                        print "Id<><><><><><:",ids.id                   
                        ps.browse(ids.id).write({'status':'on intransit'})
                    
        except Exception as err:
            self._cr.rollback()
            self.env['b2b.file'].insert_error_monitoring('gagal_import',obj=file_obj,additional=err)
            file_obj.write({
                'state' : 'error'
            })
            res = False
        finally :
            self._cr.commit()
        return res