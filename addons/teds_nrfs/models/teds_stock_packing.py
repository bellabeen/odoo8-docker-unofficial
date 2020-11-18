from openerp import models, fields, api

class teds_stock_packing(models.Model):
    _inherit = "wtc.stock.packing"

    def _create_nrfs(self):
        for x in self.packing_line:
            if not x.ready_for_sale:
                fm_obj = self.env['b2b.file.fm'].suspend_security().search([('no_mesin','=',x.serial_number_id.name)])
                self.env['teds.nrfs'].suspend_security().create({
                    'branch_id': self.branch_id.id,
                    'lot_id': x.serial_number_id.id,
                    'tipe_nrfs': 'LKUAT',
                    'origin': self.name,
                    'tgl_nrfs': self._get_default_date(),
                    'nopol_ekspedisi': self.plat_number_id.id if self.plat_number_id else False,
                    'driver_ekspedisi': self.driver_id.id if self.driver_id else False,
                    'kapal_ekspedisi': fm_obj.nama_kapal if fm_obj else False
                })
