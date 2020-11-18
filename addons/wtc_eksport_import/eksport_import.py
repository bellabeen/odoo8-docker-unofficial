import csv
import time
import base64
import tempfile
import datetime
import StringIO
import cStringIO
from dateutil import parser
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from lxml import etree
from docutils.nodes import row

class writedata(osv.osv):
    _name = 'wtc.write.data'
    _description = 'Write Data'
    _columns = {
                'name' : fields.char(string='Name'),
                }
    
class EksportImport(osv.osv_memory):
    _name = "eksport.import"
    _columns = {
                'type': fields.selection((('eks','Export'), ('imp','Import')), 'Type'),
                'name': fields.char('File Name', 16),
                'tabel' : fields.many2one('ir.model', 'Object Model', required=True),
                'separator': fields.selection((('koma',','), ('titik_koma',';')), 'Separator'),
                'data_file': fields.binary('File'),
    }   
    _defaults = {'type' :'imp','separator':'titik_koma'}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(EksportImport, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if context.get('model') == 'journal_memorial' :
            doc = etree.XML(res['arch'])
            nodes_branch = doc.xpath("//field[@name='tabel']")
            nodes_type = doc.xpath("//field[@name='type']")
            for node in nodes_branch:
                node.set('domain', '[("model", "=", "wtc.journal.memorial")]')
            for node in nodes_type:
                node.set('value', 'imp')                
            res['arch'] = etree.tostring(doc)
        return res
        
    def eksport_excel(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        
        #[x for x in range(89153,91498)]
        idd = self.pool.get(val.tabel.model).search(cr, uid, [])
        data = self.pool.get(val.tabel.model).read(cr, uid, idd)
      
        result = ';'.join(data[0].keys())   
        value = [d.values() for d in data]
        
        for v in value:
            for x in v:
                if isinstance(x, tuple):
                    v[v.index(x)] = x[0]
        
        for row in value:
            result += '\n' + ';'.join([str(v) for v in row]) 
            
        out = base64.encodestring(result)
        self.write(cr, uid, ids, {'data_file':out, 'name': 'eksport.csv'}, context=context)
        
        view_rec = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'wtc_eksport_import', 'view_wizard_eksport_import')
        view_id = view_rec[1] or False
    
        return {
            'view_type': 'form',
            'view_id' : [view_id],
            'view_mode': 'form',
            'res_id': val.id,
            'res_model': 'eksport.import',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
             
    def import_excel(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        if not val.data_file:
            raise osv.except_osv(_('Error'), _("Silahkan memilih file yang akan diimport !"))
        
        filename = val.name
        filedata = base64.b64decode(val.data_file)
        input = cStringIO.StringIO(filedata)
        input.seek(0)
        separator = val.separator
        
        (fileno, fp_name) = tempfile.mkstemp('.csv', 'openerp_')
        file = open(fp_name, "w")
        file.write(filedata)
        file.close()
        
        crd = csv.reader(open(fp_name,"rb"))
        if separator == 'titik_koma' :
            head = crd.next()[0].split(';')
        else :
            head = crd.next()[0].split(',')
        
        fields_properties = self.fields_get(cr,uid,val.tabel.model)
        
        if val.tabel.model == 'wtc.approval.matrixbiaya.header' :
            self.approval_matrixbiaya(cr,uid,crd,head,separator)  

        elif val.tabel.model == 'wtc.approval.matrixdiscount.header' :
            self.approval_matrixdiscount(cr,uid,crd,head,separator) 
        
        elif val.tabel.model == 'hr.employee' :
            self.employee(cr,uid,crd,head,separator)   
            
        elif val.tabel.model == 'account.move.line' :
            self.account_move_line(cr,uid,crd,head,separator)      
            
        elif val.tabel.model == 'wtc.p2p.product' :
            self.p2p_product(cr,uid,crd,head,separator)   
        elif val.tabel.model == 'res.groups' :
            self.res_groups(cr,uid,crd,head,separator) 
        elif val.tabel.model == 'wtc.journal.memorial' :
            self.journal_memorial(cr,uid,crd,head,separator)             
        elif val.tabel.model == 'stock.production.lot' :
            self.stock_production_lot(cr,uid,crd,head,separator)    
        elif val.tabel.model == 'res.partner' :
            self.partner_customer(cr,uid,crd,head,separator)           
        elif val.tabel.model == 'account.asset.category' :
            self.asset_category_import(cr,uid,crd,head,separator)
        elif val.tabel.model == 'account.asset.asset' :
            self.asset_asset_import(cr,uid,crd,head,separator)       
        elif val.tabel.model == 'wtc.write.data' :
            self.write_data(cr,uid,crd,head,separator)     
            
        return {}

    def write_data(self,cr,uid,data,col,separator):
        asset_data = {}
        count = 0
        for row in data :
            count += 1

            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                
            asset_id = self.pool.get('account.asset.asset').search(cr,uid,[
                                                                           ('code','=',lis[0])
                                                                           ])

            if not asset_id :
                raise osv.except_osv(('Perhatian !'), ("Code %s tidak ditemukan !")%(lis[0]))

            asset_id = asset_id[0]
            asset_data[asset_id] = {}
            asset_data[asset_id]['real_purchase_value'] = lis[1]
            asset_data[asset_id]['real_purchase_date'] = lis[2]
        
        for key,value in asset_data.items() :
            self.pool.get('account.asset.asset').write(cr,uid,key,{
                                                                   'real_purchase_value':value['real_purchase_value'],
                                                                   'real_purchase_date': value['real_purchase_date']
                                                                   })
            print "yes"
    def asset_category_import(self, cr, uid, data, col,separator):
        vals = []
        groups_rekap = {}

        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','','','','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
                lis[6] = row[6].split(',')[0]
                lis[7] = row[7].split(',')[0]
                lis[8] = row[8].split(',')[0]
                lis[9] = row[9].split(',')[0]
                lis[10] = row[10].split(',')[0]
                lis[11] = row[11].split(',')[0]
                lis[12] = row[12].split(',')[0]

            journal_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'wtc_purchase_asset', 'journal_depresiasi_asset')[1]
            if not journal_id :
                raise osv.except_osv(('Perhatian !'), ("Journal Depresiasi tidak ditemukan !"))
            account_asset_id = self.pool.get('account.account').search(cr,uid,[
                                                          ('code','=',lis[3])
                                                          ])[0]             
            if not account_asset_id :
                raise osv.except_osv(('Perhatian !'), ("Account Asset %s tidak ditemukan !")%(lis[3])) 
                                                                                                                                       
            account_depreciation_id = self.pool.get('account.account').search(cr,uid,[
                                                          ('code','=',lis[4])
                                                          ])[0]             
            if not account_depreciation_id :
                raise osv.except_osv(('Perhatian !'), ("Account Depresiasi %s tidak ditemukan !")%(lis[4]))
                                             
            account_depreciation_expense_id = self.pool.get('account.account').search(cr,uid,[
                                                          ('code','=',lis[5])
                                                          ])[0]             
            if not account_depreciation_expense_id :
                raise osv.except_osv(('Perhatian !'), ("Account Depresiasi Expense %s tidak ditemukan !")%(lis[5]))
                                                                                 
            val = {'name':lis[0],
                   'code':lis[1],
                   'type':lis[2],
                   'account_asset_id':account_asset_id,
                   'account_depreciation_id':account_depreciation_id,
                   'account_expense_depreciation_id':account_depreciation_expense_id,
                   'method_time':lis[6],
                   'method_number':lis[7],
                   'method_period':lis[8],
                   'method':lis[9],
                   'prorata': True if lis[10] == 'TRUE' or lis[10] == 'True' or lis[10] == 'true' else False ,
                   'open_asset': True if lis[11] == 'TRUE' or lis[11] == 'True' or lis[11] == 'true' else False ,
                   'first_day_of_month': True if lis[12] == 'TRUE' or lis[12] == 'True' or lis[12] == 'true' else False ,
                   'journal_id':journal_id, 
                   }
            vals.append(val)
            
        for val in vals :    
            self.pool.get("account.asset.category").create(cr, uid, val)
            
    def asset_asset_import(self, cr, uid, data, col,separator):
        vals = []
        groups_rekap = {}

        count = 0
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','','','','','','','','','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
                lis[6] = row[6].split(',')[0]
                lis[7] = row[7].split(',')[0]
                lis[8] = row[8].split(',')[0]
                lis[9] = row[9].split(',')[0]
                lis[10] = row[10].split(',')[0]
                lis[11] = row[11].split(',')[0]
                lis[12] = row[12].split(',')[0]
                lis[13] = row[13].split(',')[0]
                lis[14] = row[14].split(',')[0]
                lis[15] = row[15].split(',')[0]
                lis[16] = row[16].split(',')[0]
                lis[17] = row[17].split(',')[0]
                
            count += 1

            branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[('code','=',lis[1])])
            if not branch_id :
                raise osv.except_osv(('Perhatian !'), ("Code Branch %s tidak ditemukan !")%(lis[1]))

            asset_category_id = self.pool.get('account.asset.category').search(cr,uid,[
                                                          ('name','=',lis[2]),
                                                          ])            
            if not asset_category_id :
                raise osv.except_osv(('Perhatian !'), ("Asset Category %s tidak ditemukan !")%(lis[2])) 
            asset_category_id = asset_category_id[0]
            categ_id = self.pool.get('account.asset.category').browse(cr,uid,asset_category_id)

            if lis[3] :                                                                                                                           
                asset_classification_id = self.pool.get('wtc.asset.classification').search(cr,uid,[
                                                              ('code','=',lis[3])])            
                if not asset_classification_id :
                    raise osv.except_osv(('Perhatian !'), ("Kode Klasifikasi Asset %s tidak ditemukan !")%(lis[3]))
                asset_classification_id = asset_classification_id[0]
            if lis[7] :                                 
                partner_id = self.pool.get('res.partner').search(cr,uid,[
                                                              ('default_code','=',lis[7])])             
                if not partner_id :
                    raise osv.except_osv(('Perhatian !'), ("Partner %s tidak ditemukan !")%(lis[7]))
                partner_id = partner_id[0]
                    
            if lis[8] :                                 
                product_id = self.pool.get('product.product').search(cr,uid,[
                                                              ('default_code','=',lis[8])])           
                if not product_id :
                    raise osv.except_osv(('Perhatian !'), ("Product %s tidak ditemukan !")%(lis[8]))
                product_id = product_id[0]
            if lis[9] :                                 
                user_id = self.pool.get('hr.employee').search(cr,uid,[
                                                              ('nip','=',lis[9])])          
                if not user_id :
                    raise osv.except_osv(('Perhatian !'), ("NIP Responsible %s tidak ditemukan !")%(lis[9]))
                user_id = user_id[0]      
                                                                                                        
            val = {'name':lis[0],
                   'branch_id':branch_id[0] ,
                   'category_id':asset_category_id,
                   'asset_classification_id':asset_classification_id if lis[3] else False,
                   'purchase_date':lis[4],
                   'purchase_value':lis[5],
                   'salvage_value':lis[6],
                   'partner_id':partner_id if lis[7] else False,
                   'product_id':product_id if lis[8] else False,
                   'responsible_id':user_id if lis[9] else False,
                   'note':lis[10],
                   'method_time':lis[11] if lis[11] else categ_id.method_time,
                   'method_number':lis[12] if lis[12] else categ_id.method_number,
                   'method_period':lis[13] if lis[13] else categ_id.method_period,        
                   'method':lis[14] if lis[14] else categ_id.method,           
                   'prorata':lis[15] if lis[15] else categ_id.prorata,
                   'first_day_of_month':lis[16] if lis[16] else categ_id.first_day_of_month, 
                   'code':lis[17] if lis[17] else False,             
                   }
            vals.append(val)
            
        for val in vals :    
            asset = self.pool.get("account.asset.asset").create(cr, uid, val)
#             self.pool.get('account.asset.asset').validate(cr,uid,asset)
                        
#GROUPS BY ID
    def res_groups(self, cr, uid, data, col,separator):
        vals = []
        groups_rekap = {}
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                            
            lis = row[0].split(separator)
            if int(lis[0]) not in groups_rekap :
                groups_rekap[int(lis[0])] = []
                groups_rekap[int(lis[0])].append((4,int(lis[1])))
            else :
                groups_rekap[int(lis[0])].append((4,int(lis[1])))
        for key,value in groups_rekap.items() :
            self.pool.get('res.groups').write(cr,uid,[key],{
          
                                                             'implied_ids':value                                                                                
                                                             })  
                 
    def journal_memorial(self, cr, uid, data, col,separator):
        vals = []
        count = 0
        
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
                lis[6] = row[6].split(',')[0]
                lis[7] = row[7].split(',')[0]
                lis[8] = row[8].split(',')[0]
                lis[9] = row[9].split(',')[0]
                lis[10] = row[10].split(',')[0]
                
            partner_id = False
            asset_id = False
            count += 1
            if lis[5]:
                partner_id = self.pool.get('res.partner').search(cr,SUPERUSER_ID,[
                                                                       ('default_code','=',lis[5])
                                                                       ])
                if not partner_id :
                    raise osv.except_osv(('Perhatian !'), ("Code Partner %s tidak ditemukan !")%(lis[5]))
                partner_id = partner_id[0]
            if lis[10]:
                asset_id = self.pool.get('account.asset.asset').search(cr,SUPERUSER_ID,[
                                                                                        ('code','=',lis[10])
                                                                                        ])
                if not asset_id :
                    raise osv.except_osv(('Perhatian !'), ("Code Asset %s tidak ditemukan !")%(lis[10]))
                asset_id = asset_id[0]                                                                                    
                      
            branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                                   ('code','=',lis[6])
                                                                   ])
            if not branch_id :
                raise osv.except_osv(('Perhatian !'), ("Code Branch %s tidak ditemukan !")%(lis[6]))
               
            account_id = self.pool.get('account.account').search(cr,SUPERUSER_ID,[
                                                                   ('code','=',lis[7])
                                                                   ])
            if not account_id :
                raise osv.except_osv(('Perhatian !'), ("Code Account %s tidak ditemukan !")%(lis[7]))
                
                                
            line = [0,False,{
                             'partner_id':partner_id,
                             'branch_id':branch_id[0],
                             'account_id':account_id[0],
                             'type':lis[8],
                             'amount':lis[9],
                             'asset_id' : asset_id,
                             }]
            
            if not lis[0] :
                vals[len(vals)-1]['journal_memorial_line'].append(line)
            else :
                branch_header_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                                       ('code','=',lis[0])
                                                                       ])
                if not branch_header_id :
                    raise osv.except_osv(('Perhatian !'), ("Code Branch %s tidak ditemukan !")%(lis[0]))
                
                period_id = self.pool.get('account.period').search(cr,SUPERUSER_ID,[
                                                                       ('code','=',lis[1])
                                                                       ])
                if not period_id :
                    raise osv.except_osv(('Perhatian !'), ("Code Peride %s tidak ditemukan !")%(lis[1]))
                if lis[3] not in ('FALSE','TRUE') :
                    raise osv.except_osv(('Perhatian !'), ("Tolong isi auto reverse dengan 'FALSE' atau 'TRUE' !"))
                if lis[4] not in ('Unit','Sparepart','Umum','Finance') :
                    raise osv.except_osv(('Perhatian !'), ("Tolong isi division dengan 'Unit','Finance', 'Umum' atau 'Sparepart' !"))
                if lis[8] not in ('Dr','Cr') :
                    raise osv.except_osv(('Perhatian !'), ("Tolong isi Type dengan 'Dr' atau 'Cr' !"))
                auto_reverse = False 
                if lis[3] == 'TRUE' :
                    auto_reverse = True                                                                                           
                val = {'branch_id':branch_header_id[0],'periode_id':period_id[0],'description':lis[2],'auto_reverse':auto_reverse,'division':lis[4],'journal_memorial_line':[]}
                val['journal_memorial_line'].append(line)
                vals.append(val)
        for val in vals :    
            self.pool.get("wtc.journal.memorial").create(cr, uid, val)
                                 
    def approval_matrixbiaya(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
            
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, lis[4].split('.')[0], lis[4].split('.')[1])[1]            
            line = [0,False,{'group_id':group_id,'limit':float(lis[5])}]
            
            if not lis[0] :
                vals[len(vals)-1]['approval_line'].append(line)
            else :
                config = self.pool.get("wtc.approval.config").search(cr,uid,[
                                                                          ('name','=',lis[1])
                                                                          ])
                branch_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, lis[0].split('.')[0], lis[0].split('.')[1])[1]
                val = {'branch_id':branch_id,'form_id':config[0],'division':lis[3],'approval_line':[]}
                val['approval_line'].append(line)
                vals.append(val)
            
        for val in vals :    
            self.pool.get("wtc.approval.matrixbiaya.header").create(cr, uid, val)
                        
    def approval_matrixdiscount(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
            
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, lis[4].split('.')[0], lis[4].split('.')[1])[1]
            product_id = self.pool.get('product.template').search(cr,uid,[
                                                                          ('name','=',lis[3])
                                                                          ])            
            line = [0,False,{'group_id':group_id,'limit':float(lis[5])}]
            
            if not lis[0] :
                vals[len(vals)-1]['wtc_approval_md_ids'].append(line)
            else :
                config = self.pool.get("wtc.approval.config").search(cr,uid,[
                                                                          ('name','=',lis[2])
                                                                          ])
                branch_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, lis[0].split('.')[0], lis[0].split('.')[1])[1]
                val = {'branch_id':branch_id,'form_id':config[0],'division':lis[1],'wtc_approval_md_ids':[],'product_template_id':product_id[0]}
                val['wtc_approval_md_ids'].append(line)
                vals.append(val)
            
        for val in vals :    
            self.pool.get("wtc.approval.matrixdiscount.header").create(cr, uid, val)     
            
    def employee(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
            job_id = self.pool.get('hr.job').search(cr,uid,[
                                                          ('name','=',lis[3])
                                                          ]) 
            if not job_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ada Job title %s dalam master Job!")%(lis[3]))
            branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                          ('code','=',lis[4])
                                                          ])             
            if not branch_id :
                raise osv.except_osv(('Perhatian !'), ("Branch %s tidak ditemukan !")%(lis[4]))
            
            area_id = self.pool.get('wtc.area').search(cr,uid,[
                                                          ('code','=',lis[5])
                                                          ])             
            if not area_id :
                raise osv.except_osv(('Perhatian !'), ("Area %s tidak ditemukan !")%(lis[5]))                        

            config = self.pool.get("wtc.approval.config").search(cr,uid,[
                                                                      ('name','=',lis[2])
                                                                      ])
            val = {'branch_id':branch_id[0],'nip':lis[0],'name':lis[1],'job_id':job_id[0],'area_id':area_id[0],'tgl_masuk':lis[2]}
            vals.append(val)
            
        for val in vals :    
            self.pool.get("hr.employee").create(cr, uid, val)            

    def partner_customer(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
            
            branch_id = False
            if lis[2] :
                branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                              ('code','=',lis[2])
                                                              ])[0]             
                if not branch_id :
                    raise osv.except_osv(('Perhatian !'), ("Branch %s tidak ditemukan !")%(lis[2]))

            val = {'branch_id':branch_id,'nip':lis[0],'default_code':lis[0],'name':lis[1],'customer':True}
            vals.append(val)
            
        for val in vals :    
            self.pool.get("res.partner").create(cr, uid, val,context={'form_name':'Customer'})  

            
    def p2p_product(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]

            product_id = self.pool.get('product.product').browse(cr,uid,lis[0]).id
            if not product_id :
                raise osv.except_osv(('Perhatian !'), ("Product %s tidak ditemukan !")%(lis[0]))

            val = {'product_id':product_id,'start_date':lis[1],'end_date':lis[2]}
            vals.append(val)
            
        for val in vals :    
            self.pool.get("wtc.p2p.product").create(cr, uid, val)
            
    def stock_production_lot(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','','','','','','','','','','','','','','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
                lis[6] = row[6].split(',')[0]
                lis[7] = row[7].split(',')[0]
                lis[8] = row[8].split(',')[0]
                lis[9] = row[9].split(',')[0]
                lis[10] = row[10].split(',')[0]
                lis[11] = row[11].split(',')[0]
                lis[12] = row[12].split(',')[0]
                lis[13] = row[13].split(',')[0]
                lis[14] = row[14].split(',')[0]
                lis[15] = row[15].split(',')[0]
                lis[16] = row[16].split(',')[0]
                lis[17] = row[17].split(',')[0]
                lis[18] = row[18].split(',')[0]
                lis[19] = row[19].split(',')[0]
                lis[20] = row[20].split(',')[0]
                lis[21] = row[21].split(',')[0]
                lis[22] = row[22].split(',')[0]
                lis[23] = row[23].split(',')[0]
                
                
            branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                          ('code','=',lis[2])
                                                          ])   

            if not branch_id :
                raise osv.except_osv(('Perhatian !'), ("Branch %s tidak ditemukan !")%(lis[2]))

            product_id = self.pool.get('product.product').search(cr,uid,[
                                                          ('name','=',lis[3])
                                                          ])             
            if not product_id :
                raise osv.except_osv(('Perhatian !'), ("Product %s tidak ditemukan !")%(lis[3]))
            
            birojasa_id = self.pool.get('res.partner').search(cr,uid,[
                                                          ('rel_code','=',lis[4])
                                                          ])             
            if not birojasa_id :
                raise osv.except_osv(('Perhatian !'), ("Birojasa %s tidak ditemukan !")%(lis[4]))
 
            customer_id = self.pool.get('res.partner').search(cr,uid,[
                                                          ('rel_code','=',lis[6])
                                                          ])             
            if not customer_id :
                raise osv.except_osv(('Perhatian !'), ("Customer %s tidak ditemukan !")%(lis[6]))
                         
            customer_stnk_id = self.pool.get('res.partner').search(cr,uid,[
                                                          ('rel_code','=',lis[7])
                                                          ])             
            if not customer_stnk_id :
                raise osv.except_osv(('Perhatian !'), ("Customer STNK %s tidak ditemukan !")%(lis[7]))
                               
            finco_id = False
            if lis[8] != 'FALSE' :
                finco_id = self.pool.get('res.partner').search(cr,uid,[
                                                              ('code','=',lis[8])
                                                              ])             
                if not finco_id :
                    raise osv.except_osv(('Perhatian !'), ("Fincoy %s tidak ditemukan !")%(lis[8]))
                else :
                    finco_id = finco_id[0]                                     
            val = {'name':lis[0],
                   'chassis_no':lis[1],
                   'branch_id':branch_id[0],
                   'product_id':product_id[0],
                   'biro_jasa_id':birojasa_id[0],
                   'tgl_faktur':lis[5] if lis[5] != '' else False,
                   'customer_id':customer_id[0],
                   'customer_stnk':customer_stnk_id[0],
                   'finco_id':finco_id,
                   'jenis_penjualan':lis[9] if lis[9] != '' else False,
                   'tgl_terima':lis[10] if lis[10] != '' else False,
                   'tgl_proses_stnk':lis[11] if lis[11] != '' else False,
                   'invoice_bbn':lis[12] if lis[12] != '' else False,
                   'tgl_proses_birojasa':lis[13] if lis[13] != '' else False,
                   'tgl_terima_notice':lis[14] if lis[14] != '' else False,
                   'tgl_terima_stnk':lis[15] if lis[15] != '' else False,
                   'no_stnk':lis[16] if lis[16] != '' else False,
                   'tgl_terima_no_polisi':lis[17] if lis[17] != '' else False,
                   'no_polisi':lis[18] if lis[18] != '' else False,
                   'tgl_terima_bpkb':lis[19] if lis[19] != '' else False,
                   'no_bpkb':lis[20] if lis[20] != '' else False,
                   'tgl_penyerahan_stnk':lis[21] if lis[21] != '' else False,
                   'tgl_penyerahan_plat':lis[22] if lis[22] != '' else False,
                   'tgl_penyerahan_bpkb':lis[23] if lis[23] != '' else False,
                   'state':'paid',
                   'state_stnk':'proses_stnk',
                   'lot_status_cddb':'ok',
                   'division':'Unit'
                   }
            vals.append(val)
            
        for val in vals :    
            self.pool.get("stock.production.lot").create(cr, uid, val)
                        
    def account_move_line(self, cr, uid, data, col,separator):
        vals = []
        for row in data:
            if separator == 'titik_koma' :
                lis = row[0].split(';')
            else :
                lis = ['','','','','','','','','','','','','']
                lis[0] = row[0].split(',')[0]
                lis[1] = row[1].split(',')[0]
                lis[2] = row[2].split(',')[0]
                lis[3] = row[3].split(',')[0]
                lis[4] = row[4].split(',')[0]
                lis[5] = row[5].split(',')[0]
                lis[6] = row[6].split(',')[0]
                lis[7] = row[7].split(',')[0]
                lis[8] = row[8].split(',')[0]
                lis[9] = row[9].split(',')[0]
                lis[10] = row[10].split(',')[0]
                lis[11] = row[11].split(',')[0]
                lis[12] = row[12].split(',')[0]   
                             
            for i in range(0,len(lis)-1):
                lis[i] = lis[i].strip()
                
            partner_id = False
            account_id = False
            journal_id = False
            period_id = False
            branch_id = False
            
            if lis[0] :            
                journal_id = self.pool.get('account.journal').search(cr,uid,[
                                                              ('name','=',lis[0])
                                                              ]) 
                if not journal_id :
                    raise osv.except_osv(('Perhatian !'), ("Journal %s tidak ditemukan !")%(lis[0]))
            if lis[1] :
                period_id = self.pool.get('account.period').search(cr,uid,[
                                                              ('name','=',lis[1])
                                                              ])             
                if not period_id :
                    raise osv.except_osv(('Perhatian !'), ("Period %s tidak ditemukan !")%(lis[1]))
            if lis[5] :
                branch_id = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[
                                                              ('code','=',lis[5])
                                                              ])             
                if not branch_id :
                    raise osv.except_osv(('Perhatian !'), ("Branch %s tidak ditemukan !")%(lis[5]))                        
            if lis[8] :
                partner_id = self.pool.get('res.partner').search(cr,uid,[
                                                              ('default_code','=',lis[8])
                                                              ])             
                if not partner_id :
                    raise osv.except_osv(('Perhatian !'), ("Partner %s tidak ditemukan !")%(lis[8]))  
            if lis[9] :
                account_id = self.pool.get('account.account').search(cr,uid,[
                                                              ('code','=',lis[9])
                                                              ])             
                if not account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account %s tidak ditemukan !")%(lis[9]))  
              
            val = {'journal_id':journal_id[0] if journal_id else False,
                   'period_id':period_id[0] if period_id else False,
                   'ref':lis[2],
                   'date':lis[3],
                   'narration':lis[4],
                   'branch_id':branch_id[0] if branch_id else False,
                   'division':lis[6],
                   'name':lis[7],
                   'partner_id':partner_id[0] if partner_id else False,
                   'account_id':account_id[0] if account_id else False,
                   'date_maturity':lis[10] if lis[10] else False,
                   'debit':float(lis[11].replace(" ","")) if lis[11].replace(" ","") else 0.0,
                   'credit':float(lis[12].replace(" ","")) if lis[12].replace(" ","") else 0.0
                   }
            vals.append(val)
            
        for val in vals :    
            self.pool.get("account.move.line").create(cr, uid, val)                
EksportImport()
