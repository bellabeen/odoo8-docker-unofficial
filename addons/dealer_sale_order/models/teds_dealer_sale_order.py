from openerp import models, fields, api
from openerp.exceptions import Warning
import time
from openerp.osv import osv
from openerp.report import report_sxw

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"
    
    surat_kuasa_type = fields.Selection([('SOH','SOH'),('Biro Jasa','Biro Jasa')],string="Surat Kuasa")
    
    @api.multi
    def write(self,vals):
        write = super(DealerSaleOrder,self).write(vals)
        hl_ids = []
        for hl in self.hutang_lain_line:
            if hl.hl_id.id in hl_ids:
                raise Warning('Hutang Lain tidak boleh duplikat !')
            hl_ids.append(hl.hl_id.id)
        return write


    @api.multi
    def action_print_surat_kuasa_dso(self):
        self.ensure_one()
        form_id = self.env.ref('dealer_sale_order.view_dso_surat_kuasa_wizard').id
        return {
            'name': ('Print Surat Kuasa'),
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_print_surat_kuasa_dso_pdf(self):
        datas = self.read()[0]
        kuasa_kepada = ''
        if self.surat_kuasa_type == 'SOH':
            soh = self.env['hr.employee'].sudo().search([
                ('branch_id','=',self.branch_id.id),
                ('job_id.sales_force','=','soh'),
                ('tgl_keluar','=',False)],limit=1)
            if not soh:
                raise Warning('Tidak ditemukan data SOH pada employee !')
            kuasa_kepada = soh.name_related
        else:
            kuasa_kepada = self.env['dealer.sale.order.line'].search([('dealer_sale_order_line_id','=',self.id)],limit=1).biro_jasa_id.name
        datas['kuasa_kepada'] = kuasa_kepada
        return self.env['report'].get_action(self,'dealer_sale_order.teds_print_surat_kuasa_dso_pdf', data=datas)


class DealerSaleOrderLine(models.Model):
    _inherit = "dealer.sale.order.line"

    tenor_list = fields.Selection([('12','12'),('18','18'),('24','24'),('36','36'),('lainnya','Lainnya')])

    @api.onchange('finco_tenor')
    def onchange_tenor(self):
        if self.finco_tenor:
            if len(str(self.finco_tenor)) > 2:
                warning = {'title':'Perhatian !','message':'Harap cek kembali data tenor !'}
                self.finco_tenor = False
                return {'warning':warning}
    
    @api.onchange('cicilan')
    def onchange_cicilan(self):
        if self.cicilan:
            if len(str(self.cicilan)) < 6:
                warning = {'title':'Perhatian !','message':'Harap cek kembali data cicilan!'}
                self.cicilan = False
                return {'warning':warning}

    
    @api.onchange('tenor_list')
    def onchange_tenor_list(self):
        self.finco_tenor = False
        if self.tenor_list:
            if self.tenor_list != 'lainnya':
                self.finco_tenor = self.tenor_list


class SuratKuasaDSOPrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(SuratKuasaDSOPrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data

class SuratKuasaDSOPrint(osv.AbstractModel):
    _name = 'report.dealer_sale_order.teds_print_surat_kuasa_dso_pdf'
    _inherit = 'report.abstract_report'
    _template = 'dealer_sale_order.teds_print_surat_kuasa_dso_pdf'
    _wrapped_report_class = SuratKuasaDSOPrintData






    
