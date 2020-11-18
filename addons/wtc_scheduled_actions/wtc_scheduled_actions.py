from openerp import models, fields, api

class wtc_scheduled_actions(models.Model):
    _name = "wtc.scheduled.actions"
    
    
    ## Reset Monthly Sequence
    ## Expected runs on First Day of Every Month
    @api.multi
    def action_reset_sequence(self):
        sequences = self.env['ir.sequence'].search(['|',('prefix','like','%(month)s%'),('suffix','like','%(month)s%')])
        #sequences.write({'number_next':1})
        for seq in sequences:
            if seq.implementation=='standard':
                self._cr.execute("""alter sequence ir_sequence_%03d restart with 1""" % seq.id)
            else:
                seq.write({'number_next':1})
        
    @api.multi
    def action_garbage_report(self):
        self._cr.execute("""
                        delete from wtc_report_piutang_wizard;
                        delete from wtc_wo_wip_report;
                        delete from wtc_report_journal;
                        delete from wtc_report_pembelian_wizard;
                        delete from wtc_report_so_undelivered;
                        delete from wtc_report_intransit_beli;
                        delete from wtc_report_penjualan_wizard;
                        delete from wtc_report_asset_wizard;
                        delete from wtc_report_cash;
                        delete from wtc_report_control_df;
                        delete from wtc_report_hutang_wizard;
                        delete from wtc_report_penjualan_md_wizard;
                        delete from report_stnk_bpkb;
                        delete from wtc_report_stock_movement_wizard;
                        delete from wtc_report_bank_transfer_wizard;
                        delete from wtc_report_data_konsumen;
                        delete from wtc_report_incentive_sale_wizard;
                        delete from wtc_report_mutasi_detil;
                        delete from report_stnk_bpkb;
                        delete from wtc_report_lbb_wizard;
                        
        """)

    
