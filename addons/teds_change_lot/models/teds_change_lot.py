# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, api, models, _
from openerp.exceptions import Warning
from datetime import datetime
import string

class ChangeLot(models.Model) :
    _name        = "teds.change.lot"
    _description = "Change Lot"
    _order       = "date desc"
    _rec_name    = "lot_id"
    _inherit     = "mail.thread"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("waiting_for_approval","Waiting For Approval"),
        ("approved","Approved"),
        ("confirm","Confirmed"),
        ("cancel","Cancelled")
    ]
    
    APPROVAL_STATE_SELECTION = [
        ("b","Belum Request"),
        ("rf","Request For Approval"),
        ("a","Approved"),
        ("r","Reject")
    ]

    @api.model
    def _get_default_date(self):
        return self.env["wtc.branch"].get_default_date_model()

    @api.model
    def _get_default_branch(self):
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    name                            = fields.Char("Change Number")
    branch_id                       = fields.Many2one("wtc.branch",string="Branch",default=_get_default_branch)
    division                        = fields.Selection([("Unit", "Unit")], "Division", default="Unit")
    lot_id                          = fields.Many2one("stock.production.lot",string="Serial Number")

    old_partner_id                  = fields.Many2one("res.partner",string="Customer")
    old_partner_name                = fields.Char("Customer Name")
    old_customer_stnk_id            = fields.Many2one("res.partner",string="Customer STNK")
    old_no_stnk                     = fields.Char("No STNK")
    old_no_bpkb                     = fields.Char("No BPKB")
    old_no_polisi                   = fields.Char("No Polisi")
    old_name                        = fields.Char("Engine No")
    old_chassis_no                  = fields.Char("Chassis Number")
    old_no_notice                   = fields.Char("No Notice")
    old_no_faktur                   = fields.Char("No Faktur")

    old_related_partner_id          = fields.Many2one("res.partner",string="Customer",related="old_partner_id",readonly=True)
    old_related_partner_name        = fields.Char("Customer Name",related="old_partner_name",readonly=True)
    old_related_customer_stnk_id    = fields.Many2one("res.partner",string="Customer STNK",related="old_customer_stnk_id",readonly=True)
    old_related_no_stnk             = fields.Char("No STNK",related="old_no_stnk",readonly=True)
    old_related_no_bpkb             = fields.Char("No BPKB",related="old_no_bpkb",readonly=True)
    old_related_no_polisi           = fields.Char("No Polisi",related="old_no_polisi",readonly=True)
    old_related_name                = fields.Char("Engine No",related="old_name",readonly=True)
    old_related_chassis_no          = fields.Char("Chassis Number",related="old_chassis_no",readonly=True)
    old_related_no_notice           = fields.Char("No Notice",related="old_no_notice",readonly=True)
    old_related_no_faktur           = fields.Char("No Faktur",related="old_no_faktur",readonly=True)

    new_partner_id                  = fields.Many2one("res.partner",string="Customer")
    new_partner_name                = fields.Char("Customer Name")
    new_customer_stnk_id            = fields.Many2one("res.partner",string="Customer STNK")
    new_no_stnk                     = fields.Char("No STNK")
    new_no_bpkb                     = fields.Char("No BPKB")
    new_no_polisi                   = fields.Char("No Polisi")
    new_name                        = fields.Char("Engine No")
    new_chassis_no                  = fields.Char("Chassis Number")
    new_no_notice                   = fields.Char("No Notice")
    new_no_faktur                   = fields.Char("No Faktur")

    state                           = fields.Selection(STATE_SELECTION, string="State", readonly=True, default="draft")
    date                            = fields.Datetime("Date",default=_get_default_date)
    confirm_uid                     = fields.Many2one("res.users",string="Confirmed by")
    confirm_date                    = fields.Datetime("Confirmed on")

    approval_ids                    = fields.One2many("wtc.approval.line","transaction_id",string="Table Approval",domain=[("form_id","=",_name)])
    approval_state                  = fields.Selection(APPROVAL_STATE_SELECTION, string="Approval State", readonly=True, default="b")

    note                            = fields.Text(string="Catatan")

    @api.multi
    def is_punctuation(self, words):
        for n in range(len(words)) :
            if words[n] in string.punctuation :
                return True
        return False

    @api.onchange("branch_id","lot_id")
    def onchange_lot(self):
        if self.branch_id and self.lot_id :
            lot_id                     = self.lot_id
            self.old_partner_id        = lot_id.customer_id.id
            self.old_partner_name      = lot_id.customer_id.name
            self.old_customer_stnk_id  = lot_id.customer_stnk.id
            self.old_no_stnk           = lot_id.no_stnk
            self.old_no_bpkb           = lot_id.no_bpkb
            self.old_no_polisi         = lot_id.no_polisi
            self.old_name              = lot_id.name
            self.old_chassis_no        = lot_id.chassis_no
            self.old_no_notice         = lot_id.no_notice
            self.old_no_faktur         = lot_id.no_faktur

    @api.onchange("new_no_stnk","new_no_bpkb","new_no_polisi")
    def onchange_new_lot(self):
        if self.new_no_stnk :
            self.new_no_stnk    = self.new_no_stnk.upper()
        if self.new_no_bpkb :
            self.new_no_bpkb    = self.new_no_bpkb.upper()
        if self.new_no_polisi :
            self.new_no_polisi  = self.new_no_polisi.upper()

    @api.onchange("new_name","new_chassis_no")
    def onchange_kode_mesin(self):
        if self.new_name or self.new_chassis_no :
            warning = {}
            product_id = self.lot_id.product_id
            if not product_id.kd_mesin :
                self.new_name = False
                warning['title'] = _('Perhatian !')
                warning['message'] = _('Kd Mesin belum diisi dalam Master Produk')
                return {'warning': warning}

            product_id.kd_mesin = product_id.kd_mesin.replace(' ', '')
            pjg = len(product_id.kd_mesin)

            if self.new_name :
                self.new_name       = self.new_name.upper()
                if len(self.new_name) != 12 :
                    self.new_name = False
                    warning["title"]    =  _("Perhatian !")
                    warning['message']  = _('Nomor Engine harus 12 Digit')
                    return {'warning': warning}

                if self.is_punctuation(self.new_name):
                    self.new_name = False
                    warning = {'title': 'Perhatian', 'message': "Engine Number hanya boleh huruf dan angka"}
                    return {'warning': warning}

                if product_id.kd_mesin != self.new_name[:pjg]:
                    self.new_name = False
                    warning['title']    = _('Perhatian !')
                    warning['message']  = _('Engine Number tidak sama dengan kode mesin di Produk')
                    return {'warning': warning}

                engine_exist = self.env['stock.production.lot'].search([('name', '=', self.new_name)])
                if engine_exist:
                    self.new_name = False
                    warning = {'title': 'Perhatian !', 'message': "Engine Number sudah pernah ada"}
                    return {'warning': warning}

            if self.new_chassis_no :
                self.new_chassis_no = self.new_chassis_no.upper()
                check = False
                if len(self.new_chassis_no) == 14 or (len(self.new_chassis_no) == 17 and self.new_chassis_no[:2] == 'MH') :
                    check  = True
                if not check :
                    self.new_chassis_no = False
                    warning = {'title': 'Chassis Number Salah !',
                               'message': "Silahkan periksa kembali Chassis Number yang Anda input"}
                    return {'warning': warning}
                if self.is_punctuation(self.new_chassis_no):
                    self.new_chassis_no = False
                    warning = {'title': 'Perhatian', 'message': "Chassis Number hanya boleh huruf dan angka"}
                    return {'warning': warning}

    @api.model
    def create(self, vals, context=None):
        if not vals.get("name") :
            if vals.get("branch_id") :
                vals["name"] = self.env["ir.sequence"].get_per_branch(vals["branch_id"], "CL")
        vals["date"] = self._get_default_date()
        return super(ChangeLot, self).create(vals)

    @api.multi
    def action_request(self):
        if not self.new_no_stnk and not self.new_name and not self.new_no_bpkb and not self.new_no_polisi \
                and not self.new_chassis_no and not self.new_customer_stnk_id \
                and not self.new_partner_id and not self.new_partner_name and not self.new_no_notice:
            raise Warning('Tidak ada perubahan data!')
        self.env["wtc.approval.matrixbiaya"].request_by_value(trx=self, value=1, code=" ")
        self.write({"state":"waiting_for_approval","approval_state":"rf"})
        return True

    @api.multi
    def action_approve(self):
        approval_sts = self.env["wtc.approval.matrixbiaya"].approve(self)
        if approval_sts == 1:
            self.write({"date": self._get_default_date(), "approval_state": "a", "state": "approved"})
        elif approval_sts == 0:
            raise Warning("User tidak termasuk group Approval")
        return True

    @api.multi
    def action_confirm(self):
        vals_change_lot = {"confirm_uid"   : self._uid,
                           "confirm_date"  : datetime.now(),
                           "date"          : self._get_default_date().date(),
                           "state"         : "confirm"}

        vals_to_update = {}
        message = ''
        if self.new_partner_id :
            message                         += "<b>Customer ID  </b>"+ ' : ' + (str(self.old_partner_id.id) if self.old_partner_id else '') +' --> ' + str(self.new_partner_id.id) +'<br/>'
            vals_to_update["customer_id"]   = self.new_partner_id.id
        if self.new_partner_name :
            if self.new_partner_id :
                message                     += "<b>Customer Name</b>"+ ' : ' + self.new_partner_id.name +' --> ' + self.new_partner_name +'<br/>'
                self.new_partner_id.sudo().write({'name':self.new_partner_name})
            else :
                message                     += "<b>Customer Name</b>"+ ' : ' + (self.old_partner_name if self.old_partner_name else '') +' --> ' + self.new_partner_name +'<br/>'
                self.old_partner_id.sudo().write({'name':self.new_partner_name})
        if self.new_customer_stnk_id :
            message                         += "<b>Customer STNK</b>"+ ' : ' + 'ID= ' + (str(self.old_customer_stnk_id.id) if self.old_customer_stnk_id.id else '') + ", Name: " + (self.old_customer_stnk_id.name if self.old_customer_stnk_id else '') +' --> ' + 'ID= '+str(self.new_customer_stnk_id.id) +", Name: "+self.new_customer_stnk_id.name +'<br/>'
            vals_to_update["customer_stnk"] = self.new_customer_stnk_id.id
        if self.new_no_stnk :
            message                         += "<b>No STNK      </b>"+ ' : ' + (self.old_no_stnk if self.old_no_stnk else '') + ' --> ' + self.new_no_stnk +'<br/>'
            vals_to_update["no_stnk"]       = self.new_no_stnk
        if self.new_no_bpkb :
            message                         += "<b>No BPKB      </b>"+ ' : ' + (self.old_no_bpkb if self.old_no_bpkb else '') + ' --> ' + self.new_no_bpkb +'<br/>'
            vals_to_update["no_bpkb"]       = self.new_no_bpkb
        if self.new_no_polisi :
            message                         += "<b>No Polisi    </b>"+ ' : ' + (self.old_no_polisi if self.old_no_polisi else '') + ' --> ' + self.new_no_polisi +'<br/>'
            vals_to_update["no_polisi"]     = self.new_no_polisi
        if self.new_name :
            message                         += "<b>No Engine    </b>"+ ' : ' + (self.old_no_polisi if self.old_no_polisi else '') + ' --> ' + self.new_name +'<br/>'
            vals_to_update["name"]          = self.new_name
        if self.new_chassis_no :
            message                         += "<b>No Chassis   </b>"+ ' : ' + (self.old_chassis_no if self.old_chassis_no else '') + ' --> '+ self.new_chassis_no +'<br/>'
            vals_to_update["chassis_no"]    = self.new_chassis_no
        if self.new_no_notice :
            message                         += "<b>No Notice   </b>"+ '  : ' + (self.old_no_notice if self.old_no_notice else '') + ' --> ' + self.new_no_notice +'<br/>'
            vals_to_update["no_notice"]     = self.new_no_notice
        if self.new_no_faktur :
            message                         += "<b>No Faktur   </b>"+ '  : ' + (self.old_no_faktur if self.old_no_faktur else '') + ' --> ' + self.new_no_faktur +'<br/>'
            vals_to_update["no_faktur"]     = self.new_no_faktur


        #create mail.thread for history
        if vals_to_update :
            self.lot_id.sudo().write(vals_to_update)
        if message :
            self.message_post(body=("Perubahan Data :<br/>""%s"%message))

        self.write(vals_change_lot)
        return True

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(ChangeLot, self).unlink()
