from openerp import models, fields, api
from datetime import timedelta,datetime,date

class ApiP2p(models.Model):
    _name = "teds.api.p2p"
      

    @api.multi
    def create_p2p_aplikasi(self,vals):
        MANDATORY_FIELDS = [
            'partner_code',
            'line'
        ]
        fields = []
        for field in MANDATORY_FIELDS :
            if field not in vals.keys():
                fields.append(field)
        if len(fields) > 0:
            return {
                'status': 0,
                'error': 'mandatory_field',
                'remark': 'Fields ini tidak ada: %s.' % str(fields),
            }

        partner_code = vals['partner_code']
        line_ids = vals['line']

        if not partner_code:
            return {
                'status':0,
                'error':'empty_field',
                'remark':'Fields required harus diisi',
            }

        partner = self.env['res.partner'].sudo().search([('default_code','=',partner_code)],limit=1)
        if not partner:
            return {
                'status':0,
                'error':'data_not_found',
                'remark':'Partner Code %s' %(partner_code)
            }

        

        dealer_id = partner.id
        supplier_id = partner.branch_id.partner_id.id
        periode = self.env['wtc.p2p.periode'].search([
            ('start_date','<=',date.today()),
            ('end_date','>=',date.today())], order='name',limit=1).name
        type_id = self.env['wtc.purchase.order.type'].sudo().search([
            ('category','=','Sparepart'),
            ('name','=','Additional')],limit=1)
        if not type_id:
            return {
                'status':0,
                'error':'data_not_found',
                'remark':'Purchase Order Type'
            }
        line = []
        MANDATORY_FIELDS_LINE = [
            'product_code',
            'qty',
        ]
        field_line = []
        for x in line_ids:
            for field in MANDATORY_FIELDS_LINE:        
                if field not in x.keys():
                    field_line.append(field)
                
            if len(field_line) > 0:
                return {
                    'status': 0,
                    'error': 'mandatory_field',
                    'remark': 'Fields detail ini tidak ada: %s.' % str(field_line),
                }
            product_code = x['product_code']
            qty = x['qty']
            if not product_code:
                return {
                    'status': 0,
                    'error': 'empty_field',
                    'remark': 'Product harus diisi',
                }

            product = self.env['product.product'].sudo().search([('name','=',product_code)],limit=1) 
            if not product:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'Product Code %s' %(product_code)
                } 


            line.append([0,False,{
                'product_id':product.id,
                'fix_qty':qty,
            }])
        if len(line) <= 0:
            return {
                'status':0,
                'error':'line_empty',
                'remark':'Data line tidak boleh kosong'
            } 


        create = self.env['wtc.p2p.purchase.order'].sudo().create({
            'dealer_id':dealer_id,
            'supplier_id':supplier_id,
            'division':'Sparepart',
            'periode_id':periode,
            'description':vals.get('description',False),
            'purchase_order_type_id':type_id.id,
            'type_name':type_id.name,
            'additional_line':line
        })

        return {
            'status':1,
            'data':{'id':create.id,'name':create.name}
        }


