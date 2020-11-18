import tempfile
import pytz
from datetime import date, datetime, timedelta
from openerp import models, fields, api

class teds_mft_nrfs_ppo(models.Model):
    _inherit = "teds.mft.file"

    @api.multi
    def mft_generate_ppo_urgent(self):
        get_ppo_query = """
            SELECT
                nrfs.id AS nrfs_id,
                nrfs.no_po_urg,
                'H2Z;' 
                || TO_CHAR(nrfsl.tgl_po_urg, 'DDMMYYYY') || ';' 
                || 'URG;'
                || nrfsl.no_po_urg || ';' 
                || CAST(ROW_NUMBER() OVER () AS VARCHAR) || ';'
                || pt.name || ';' 
                || CAST(nrfsl.qty AS VARCHAR) || ';'
                || TO_CHAR((DATE(nrfsl.tgl_po_urg) + INTERVAL '10 day')::DATE, 'DDMMYYYY')
                || ';;;H2Z;' 
                || COALESCE(REPLACE(b.name, 'Cabang', 'TDM'),'') || ';' 
                || COALESCE(b.street,'') || ';' 
                || COALESCE(city.name,'') || ';'
                || COALESCE(kel.zip,'') || ';'
                || COALESCE(pt_unit.name,'') || ';'
                || COALESCE(lot.tahun,'') || ';'
                || COALESCE(b.code,'') || ';'
                || TO_CHAR(nrfsl.tgl_po_urg, 'DDMMYYYY') || ';;'
                || b.phone || ';;;' AS datas
                -- minus master gejala & master penyebab
            FROM teds_nrfs nrfs
            JOIN teds_nrfs_line nrfsl ON nrfs.id = nrfsl.lot_id
            JOIN product_product pp ON nrfsl.part_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN res_partner p ON nrfs.branch_partner_id = p.id
            JOIN wtc_branch b ON p.id = b.partner_id
            LEFT JOIN wtc_city city ON b.city_id = city.id
            LEFT JOIN wtc_kelurahan kel ON b.zip_code_id = kel.id
            JOIN stock_production_lot lot ON nrfs.lot_id = lot.id
            JOIN product_product pp_unit ON lot.product_id = pp_unit.id
            JOIN product_template pt_unit ON pp_unit.product_tmpl_id = pt_unit.id
            WHERE nrfsl.is_po_urgent = True
            AND nrfsl.no_po_urg IS NOT NULL
            AND nrfsl.tgl_po_urg IS NOT NULL
            AND nrfs.mft_ppo_urg = False
            AND nrfs.nama_file_ppo_urg IS NULL
            AND nrfs.tgl_kirim_ppo_urg IS NULL
        """
        self._cr.execute(get_ppo_query)
        po_ress = self._cr.dictfetchall()
        files_list = {}
        for x in po_ress:
            if x.get('datas', False):
                name = "AHM-H2Z-%s.PPO" % (str(x['no_po_urg']).replace("/",""))
                value = str(x['datas']) + "\r\n"
                if not files_list.get(name, False):
                    files_list.update({name: ""})
                    self.env['teds.nrfs'].suspend_security().browse(x['nrfs_id']).write({'mft_ppo_urg': True, 'nama_file_ppo_urg': name, 'tgl_kirim_ppo_urg': date.today()})
                files_list[name] += value
        if files_list:
            for k,v in files_list.items():
                local_path = tempfile.gettempdir() + '/' + k
                f = open(local_path, "w+")
                f.write(v)
                f.close()
                self.send_sftp(local_path)

    @api.multi
    def mft_generate_nrfs(self):
        # setup query NRFS
        get_nrfs_query = """
            SELECT
                nrfs.id,
                nrfs.tgl_selesai_actual,
                'H2Z;' 
                || TO_CHAR(nrfs.tgl_nrfs, 'YYYYMMDD') || ';' 
                || TRIM(emp.name_related) || ';'
                || pt.name || ';'
                || m_gj.code || ';'
                || m_sbb.code || ';'
                || lot.name || ';'
                || 'MH1' || lot.chassis_no || ';'
                || TO_CHAR(lot.receive_date, 'YYYYMMDD') || ';'
                || COALESCE(m_pu.code,'') || ';'
                || p.id_ekspedisi_ahm || ';'
                || pn.plat_number || ';'
                || COALESCE(nrfs.kapal_ekspedisi,'') || ';'
                || CASE
                        WHEN nrfsl.is_po_urgent = False OR nrfsl.is_po_urgent IS NULL THEN 'N;;'
                        WHEN nrfsl.is_po_urgent != False THEN CONCAT('Y;',nrfsl.no_po_urg,';')
                   END
                || TO_CHAR(nrfs.tgl_selesai_est, 'YYYYMMDD') || ';' 
                || COALESCE(TO_CHAR(nrfs.tgl_selesai_actual, 'YYYYMMDD'),'') || ';' 
                AS datas
            FROM teds_nrfs nrfs
            JOIN teds_nrfs_line nrfsl ON nrfs.id = nrfsl.lot_id
            JOIN hr_employee emp ON nrfs.pemeriksa_id = emp.id
            JOIN product_product pp ON nrfsl.part_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN teds_nrfs_line_gejala_rel gj_rel ON nrfsl.id = gj_rel.line_id
            JOIN teds_nrfs_master_gejala m_gj ON gj_rel.gejala_id = m_gj.id
            JOIN teds_nrfs_line_penyebab_rel sbb_rel ON nrfsl.id = sbb_rel.line_id
            JOIN teds_nrfs_master_penyebab m_sbb ON sbb_rel.penyebab_id = m_sbb.id
            JOIN stock_production_lot lot ON nrfs.lot_id = lot.id
            JOIN res_partner p ON lot.expedisi_id = p.id
            JOIN wtc_plat_number_line pn ON nrfs.nopol_ekspedisi = pn.id
            LEFT JOIN teds_nrfs_master_penanganan_unit m_pu ON nrfsl.penanganan_id = m_pu.id
            WHERE (nrfs.mft_nrfs = False OR nrfs.mft_nrfs IS NULL)
            AND nrfs.state IN ('confirmed','in_progress','done')
            ORDER BY nrfs.id
        """
        self._cr.execute(get_nrfs_query)
        nrfs_ress = self._cr.dictfetchall()
        # tanggal sekarang & jam sekarang
        tz = pytz.timezone(self.env.context.get('tz')) if self.env.context.get('tz') else pytz.utc
        now = pytz.utc.localize(datetime.now()).astimezone(tz)
        filename = 'AHM-H2Z-%s-%s.NRFS' % (now.strftime('%y%m%d'), now.strftime('%y%m%d%H%M%S'))
        value = ""
        ids_list = []
        done_ids_list = []
        for x in nrfs_ress:
            # check for NULL value
            if x.get('datas',False):
                # setup value
                value += str(x['datas']) + "\r\n"
                ids_list.append(x['id'])
                if x.get('tgl_selesai_actual',False):
                    done_ids_list.append(x['id'])
        # update history MFT
        self.env['teds.nrfs'].suspend_security().browse(list(set(ids_list))).write({
            'mft_nrfs_history_ids': [[0, 0, {
                'nama_file_nrfs': filename,
                'tgl_kirim_nrfs': date.today()
            }]]
        })
        # update status MFT
        if done_ids_list:
            self.env['teds.nrfs'].suspend_security().browse(done_ids_list).write({'mft_nrfs': True})
        # send file
        if value:
            local_path = tempfile.gettempdir() + '/' + filename
            f = open(local_path, "w+")
            f.write(value)
            f.close()
            self.send_sftp(local_path)
