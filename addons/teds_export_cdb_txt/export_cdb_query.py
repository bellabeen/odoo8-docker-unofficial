import time
from datetime import datetime, timedelta
import itertools
import tempfile
from cStringIO import StringIO
import base64
import csv
import codecs
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountCSVExport(orm.TransientModel):
    _inherit = "export.cdb.txt"

    wbf = {}

        

    # def _get_header_account(self, cr, uid, ids, context=None):
    #     return [_(u'CODE'),
    #             _(u'NAME'),
    #             _(u'DEBIT'),
    #             _(u'CREDIT'),
    #             _(u'BALANCE'),
    #             ]
    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    def _get_rows_account(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        # location_status = data['location_status']
        # product_ids = data['product_ids']

        branch_ids = data['branch_ids'] 
        options = data['options']
        start_date = data['start_date']
        end_date = data['end_date']
        date = self._get_default(cr, uid, date=True, context=context)
              
        tz = '7 hours'
        
        query_where = " WHERE 1=1 "
        remark = '' 
    

        if branch_ids :
            query_where += " AND dso.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        else:
            query_where += " AND dso.branch_id is not null "

        if start_date:
            query_where += " AND date_confirm >= '%s'" %(start_date)
        if end_date:
            query_where += " AND date_confirm <= '%s'" %(end_date)


                # COALESCE(wb.code,'') ||';'||
                # COALESCE(wb.name,'') ||';'||
                # COALESCE(spl.faktur_stnk,'') ||';'||
                # dso.date_confirm ||';'||
                # COALESCE(spl.name,'') ||';'||
                # COALESCE(spl.chassis_no,'') ||';'||
                # COALESCE(spl.no_polisi,'') ||';'||
                # COALESCE(pp.name_template,'')||' '||COALESCE(pav.name,'') ||';'||
                # COALESCE(pt.description,'') ||';'||
                # COALESCE(cdb.no_ktp,'') ||';'||
                # COALESCE(cdb.name,'') ||';'||
                # cdb.birtdate ||';'||
                # COALESCE(cdb.no_telp,'') ||';'||
                # COALESCE(cdb.street,'') ||';'||
                # COALESCE(rcs.code,'') ||';'||
                # COALESCE(rcs.name,'') ||';'||
                # COALESCE(city.code,'') ||';'||
                # COALESCE(city.name,'') ||';'||
                # COALESCE(kec.code,'') ||';'||
                # COALESCE(kec.name,'') ||';'||
                # COALESCE(kel.zip,'') ||';'||
                # COALESCE(kel.name,'') ||';'||
                # COALESCE(rp.npwp,'N') ||';'||
                # 'h1' ||';'||
                # '' ||';'||
                # COALESCE(hre.sales_ahm,'TA') ||';'||
                # COALESCE(rr.name,'') ||';'||
                # COALESCE(kelamin.name,'') ||';'||
                # COALESCE(agama.name,'') ||';'||
                # COALESCE(pendidikan.name,'') ||';'||
                # COALESCE(pekerjaan.name,'') ||';'||
                # COALESCE(pengeluaran.name,'') ||';'||
                # case when dso.finco_id is null then 'Cash' else 'Credit' end ||';'||
                # COALESCE(cdb.no_hp,'') ||';'||
                # COALESCE(rp.email,'') ||';'||
                # COALESCE(hpid.name,'') ||';'||
                # COALESCE(rumah.name,'') ||';'||
                # COALESCE(hobi.name,'') ||';'||
                # COALESCE(goldar.name,'') ||';'||
                # COALESCE(cdb.dpt_dihubungi,'') ||';'||
                # case when cdb.kode_customer='G' then 'Group Customer' when cdb.kode_customer='I' then 'Individual' when cdb.kode_customer='J' then 'Join Promo' when cdb.kode_customer='C' then 'Kolektif' else null end ||';'||
                # COALESCE(penggunaan.name,'') ||';'||
                # COALESCE(pengguna.name,'') ||';'||
                # COALESCE(merk.name,'') ||';'||
                # COALESCE(jns.name,'') conten
        query = """
                select 
                COALESCE(wb.code,'')
                ,COALESCE(wb.name,'') branch
                ,COALESCE(spl.faktur_stnk,'')
                ,dso.date_confirm
                ,COALESCE(spl.name,'') engine_no
                ,COALESCE(spl.chassis_no,'')
                ,COALESCE(spl.no_polisi,'')
                ,COALESCE(pp.name_template,'')||' '||COALESCE(pav.name,'') type_color
                ,COALESCE(pt.description,'')
                ,COALESCE(cdb.no_ktp,'')
                ,COALESCE(cdb.name,'') pemilik
                ,cdb.birtdate
                ,COALESCE(cdb.no_telp,'')
                ,cdb.street
                ,COALESCE(rcs.code,'') kd_prov
                ,COALESCE(rcs.name,'') nama_prov
                ,COALESCE(city.code,'') kd_kota
                ,COALESCE(city.name,'') nama_kota
                ,COALESCE(kec.code,'') kd_kec
                ,COALESCE(kec.name,'') nama_kec
                ,COALESCE(kel.zip,'') kd_zippos
                ,COALESCE(kel.name,'') nama_kel
                ,COALESCE(rp.npwp,'')
                ,'h1' H1
                ,'' blank
                ,COALESCE(hre.sales_ahm,'')
                ,COALESCE(rr.name,'') nama_sales
                ,COALESCE(kelamin.name,'') kelamin
                ,COALESCE(agama.name,'') agama
                ,COALESCE(pendidikan.name,'') pendidikan
                ,COALESCE(pekerjaan.name,'') pekerjaan
                ,COALESCE(pengeluaran.name,'') pengeluaran
                ,case when dso.finco_id is null then 'Cash' else 'Credit' end penjualan
                ,COALESCE(cdb.no_hp,'')
                ,COALESCE(rp.email,'')
                ,COALESCE(hpid.name,'') status_hp
                ,COALESCE(rumah.name,'') status_rumah
                ,COALESCE(hobi.name,'') hobi
                ,COALESCE(goldar.name,'') golongan_darah
                ,COALESCE(cdb.dpt_dihubungi,'')
                ,case when cdb.kode_customer='G' then 'Group Customer' when cdb.kode_customer='I' then 'Individual' when cdb.kode_customer='J' then 'Join Promo' when cdb.kode_customer='C' then 'Kolektif' else null end kode_customer
                ,COALESCE(penggunaan.name,'') penggunaan
                ,COALESCE(pengguna.name,'') pengguna
                ,COALESCE(merk.name,'') merk_motor
                ,COALESCE(jns.name,'') jenis_motor
                from dealer_sale_order dso
                LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dso.id
                LEFT JOIN stock_production_lot spl on dsol.lot_id=spl.id
                LEFT JOIN product_product pp on pp.id=spl.product_id
                LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                LEFT JOIN product_category cat on pt.categ_id = cat.id
                LEFT JOIN product_category cat2 on cat.parent_id = cat2.id
                LEFT JOIN product_category cat3 on cat2.parent_id = cat3.id
                LEFT JOIN product_attribute_value_product_product_rel pavpp on pp.id = pavpp.prod_id
                LEFT JOIN product_attribute_value pav on pavpp.att_id = pav.id
                LEFT JOIN wtc_cddb cdb on cdb.id=dso.cddb_id
                LEFT JOIN res_country_state rcs on cdb.state_id=rcs.id
                LEFT JOIN wtc_city city on cdb.city_id=city.id
                LEFT JOIN wtc_kecamatan kec on cdb.kecamatan_id=kec.id
                LEFT JOIN wtc_kelurahan kel on cdb.zip_id=kel.id
                LEFT JOIN res_partner rp on dso.partner_id=rp.id
                LEFT JOIN resource_resource rr on dso.user_id=rr.user_id
                LEFT JOIN hr_employee hre on hre.resource_id=rr.id
                LEFT JOIN wtc_branch wb on wb.id=dso.branch_id
                LEFT JOIN wtc_questionnaire kelamin on cdb.jenis_kelamin_id=kelamin.id
                LEFT JOIN wtc_questionnaire agama on cdb.agama_id=agama.id
                LEFT JOIN wtc_questionnaire pendidikan on cdb.pendidikan_id=pendidikan.id
                LEFT JOIN wtc_questionnaire pekerjaan on cdb.pekerjaan_id=pekerjaan.id
                LEFT JOIN wtc_questionnaire pengeluaran on cdb.pengeluaran_id=pengeluaran.id
                LEFT JOIN wtc_questionnaire hpid on cdb.status_hp_id=hpid.id
                LEFT JOIN wtc_questionnaire rumah on cdb.status_rumah_id=rumah.id
                LEFT JOIN wtc_questionnaire hobi on cdb.hobi=hobi.id
                LEFT JOIN wtc_questionnaire goldar on cdb.gol_darah=goldar.id
                LEFT JOIN wtc_questionnaire penggunaan on cdb.penggunaan_id=penggunaan.id
                LEFT JOIN wtc_questionnaire pengguna on cdb.pengguna_id=pengguna.id
                LEFT JOIN wtc_questionnaire merk on cdb.merkmotor_id=merk.id
                LEFT JOIN wtc_questionnaire jns on cdb.jenismotor_id=jns.id
                %s;
            """ % (query_where)
        # print query
        cr.execute(query)
        date = date.strftime("%Y-%m-%d %H%M%S")
        picks = cr.fetchall()
        filename = 'Export %s %s-%s %s.txt' %(data['options'],data['start_date'],data['end_date'],date)
        
        result = '' 
        for x in picks:
            code = str(x[0].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[0] != None else ''
            branch = str(x[1].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[1] != None else ''
            faktur_stnk = str(x[2].encode('ascii','ignore').decode('ascii')).replace('\r\n', '').replace('\t','') if x[2] != None else ''
            date_confirm = str(x[3].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[3] != None else ''
            engine_no = str(x[4].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[4] != None else ''
            chassis_no = str(x[5].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[5] != None else ''
            no_polisi = str(x[6].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[6] != None else ''
            type_color = str(x[7].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[7] != None else ''
            description =str(x[8].encode('ascii','ignore').decode('ascii')).replace('\r\n', '').replace('\n', '') if x[8] != None else ''
            no_ktp = str(x[9].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[9] != None else ''
            pemilik = str(x[10].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[10] != None else ''
            birtdate = str(x[11].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[11] != None else ''
            no_telp = str(x[12].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[12] != None else ''
            street = str(x[13].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[13] != None else ''
            kd_prov = str(x[14].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[14] != None else ''
            nama_prov = str(x[15].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[15] != None else ''
            kd_kota = str(x[16].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[16] != None else ''
            nama_kota = str(x[17].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[17] != None else ''
            kd_kec = str(x[18].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[18] != None else ''
            nama_kec = str(x[19].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[19] != None else ''
            kd_zippos = str(x[20].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[20] != None else ''
            nama_kel = str(x[21].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[21] != None else ''
            npwp = str(x[22].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[22] != None else ''
            h1 = str(x[23].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[23] != None else ''
            blank = str(x[24].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[24] != None else ''
            sales_ahm = str(x[25].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[25] != None else ''
            nama_sales = str(x[26].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[26] != None else ''
            kelamin = str(x[27].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[27] != None else ''
            agama = str(x[28].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[28] != None else ''
            pendidikan = str(x[29].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[29] != None else ''
            pekerjaan = str(x[30].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[30] != None else ''
            pengeluaran = str(x[31].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[31] != None else ''
            penjualan = str(x[32].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[32] != None else ''
            no_hp = str(x[33].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[33] != None else ''
            email = str(x[34].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[34] != None else ''
            status_hp = str(x[35].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[35] != None else ''
            status_rumah = str(x[36].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[36] != None else ''
            hobi = str(x[37]).replace('\r\n', '') 
            gol_darah = str(x[38]).replace('\r\n', '')
            dpt_dihubungi = str(x[39].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[39] != None else ''
            kode_customer = str(x[40].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[40] != None else ''
            penggunaan = str(x[41].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[41] != None else ''
            pengguna = str(x[42].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[42] != None else ''
            merk_motor = str(x[43].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[43] != None else ''
            jenis_motor = str(x[44].encode('ascii','ignore').decode('ascii')).replace('\r\n', '') if x[44] != None else ''


            result += code+";"
            result += branch+";"
            result += faktur_stnk+";"
            result += date_confirm+";"
            result += engine_no+";"
            result += chassis_no+";"
            result += no_polisi+";"
            result += type_color+";"
            result += description+";" #dsdfsdfsd
            result += no_ktp+";"
            result += pemilik+";"
            result += birtdate+";"
            result += no_telp+";"
            result += street+";"
            result += kd_prov+";"
            result += nama_prov+";"
            result += kd_kota+";"
            result += nama_kota+";"
            result += kd_kec+";"
            result += nama_kec+";"
            result += kd_zippos+";"
            result += nama_kel+";"
            result += npwp+";"
            result += h1+";"
            result += blank+";"
            result += sales_ahm+";"
            result += nama_sales+";" #sdfdfg
            result += kelamin+";"
            result += agama+";"
            result += pendidikan+";"
            result += pekerjaan+";"
            result += pengeluaran+";"
            result += penjualan+";"
            result += no_hp+";"
            result += email+";"
            result += status_hp+";"
            result += status_rumah+";"
            result += hobi+";"
            result += gol_darah+";"
            result += dpt_dihubungi+";"
            result += kode_customer+";"
            result += penggunaan+";"
            result += pengguna+";"
            result += merk_motor+";"
            result += jenis_motor

            result += '\r\n';
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'name': filename,'state_x':'get', 'data_x':out,}, context=context)