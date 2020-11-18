import itertools
import tempfile
from cStringIO import StringIO
import base64
import csv
import codecs
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountCSVExport(orm.TransientModel):
    _inherit = "teds.export.crm"

    wbf = {}

        

    # def _get_header_account(self, cr, uid, ids, context=None):
    #     return [_(u'CODE'),
    #             _(u'NAME'),
    #             _(u'DEBIT'),
    #             _(u'CREDIT'),
    #             _(u'BALANCE'),
    #             ]

    def _get_rows_h1(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids'] 
        # option = data['option']

              
        tz = '7 hours'
        query_where = ""

        if branch_ids :
            query_where += " AND dso.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND dso.date_order >= '%s' " % (start_date)
        if end_date :
            query_where += " AND dso.date_order <= '%s' "  % (end_date)

      
        query="""
               select wb.code kode_dealer,
                    wb.name nama_dealer,
                    spl.no_faktur,
                    dso.date_order,
                    spl.name engine_no,
                    spl.chassis_no,
                    spl.no_polisi,
                    concat(pp.name_template,'-',pav.code)tipecolor,
                    pt.description,
                    cdb.no_ktp,
                    cdb.name nama_pembeli,
                    cdb.birtdate,
                    cdb.no_telp,
                    cdb.street,
                    concat(left(city.code,2),'0')kode_propinsi,
                    country.name as propinsi,
                    city.code kode_kota,
                    city.name kota_kab,
                    kec.code kode_kec,
                    kec.name nama_kec,
                    kel.zip zp,
                    kel.name kelurahan,
                    rp.npwp,
                    'h1' jenis_transaksi,
                    dso.amount_total,
                    hre.sales_ahm,
                    sales.name nama_sales,
                    kelamin.name jenis_kelamin,
                    agama.name agama,
                    pendidikan.name pendidikan,
                    pekerjaan.name pekerjaan,
                    pengeluaran.name pengeluaran,
                    case when dso.finco_id=null then 'Cash' else 'Credit' end jenis_pembelian,
                    cdb.no_hp,
                    rp.email,
                    status_hp.name status_hp,
                    status_rumah.name status_rumah,
                    hobi.name hobi,
                    gol_darah.name gol_darah,
                    case when cdb.dpt_dihubungi='Y' then 'Ya' else 'Tidak' end dpt_dihubungi,
                    case when kode_customer='I' then 'Individual Customer(Regular)'
                    when kode_customer='G' then 'Group Customer'
                    when kode_customer='J' then 'Individual Customer(JoinPromo)'
                    when kode_customer='C' then 'Individual Customer(Kolektif)' end kode_customer,
                    penggunaan.name penggunaan,
                    pengguna.name pengguna,
                    merkmotor.name merk_motor,
                    jenismotor.name jenis_motor
                    from dealer_sale_order dso
                    left join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dso.id
                    left join wtc_branch wb on dso.branch_id=wb.id 
                    LEFT JOIN res_partner rp on dso.partner_id=rp.id
                    left JOIN stock_production_lot spl on spl.dealer_sale_order_id=dso.id
                    LEFT JOIN product_product pp on dsol.product_id=pp.id
                    LEFT JOIN product_attribute_value_product_product_rel pavpp on pp.id=pavpp.prod_id
                    LEFT JOIN product_attribute_value pav on pavpp.att_id=pav.id
                    LEFT JOIN product_template pt on pp.product_tmpl_id=pt.id
                    LEFT JOIN res_users users on dso.user_id=users.id
                    LEFT JOIN res_partner sales on users.partner_id=sales.id
                    LEFT JOIN resource_resource rr on users.id=rr.user_id
                    LEFT JOIN hr_employee hre on hre.resource_id=rr.id
                    LEFT JOIN wtc_cddb cdb on rp.id=cdb.customer_id
                    LEFT JOIN wtc_city city on cdb.city_id=city.id
                    LEFT JOIN res_country_state country on cdb.state_id=country.id
                    LEFT JOIN wtc_kecamatan kec on cdb.kecamatan_id=kec.id
                    LEFT JOIN wtc_kelurahan kel on cdb.zip_id=kel.id
                    LEFT JOIN wtc_questionnaire kelamin on cdb.jenis_kelamin_id=kelamin.id and kelamin.type='JenisKelamin'
                    LEFT JOIN wtc_questionnaire agama on cdb.agama_id=agama.id and agama.type='Agama'
                    LEFT JOIN wtc_questionnaire pendidikan on cdb.pendidikan_id=pendidikan.id and pendidikan.type='Pendidikan'
                    LEFT JOIN wtc_questionnaire pekerjaan on cdb.pekerjaan_id=pekerjaan.id and pekerjaan.type='Pekerjaan'
                    LEFT JOIN wtc_questionnaire pengeluaran on cdb.pengeluaran_id=pengeluaran.id and pengeluaran.type='Pengeluaran'
                    LEFT JOIN wtc_questionnaire status_hp on cdb.status_hp_id=status_hp.id and status_hp.type='Status HP'
                    LEFT JOIN wtc_questionnaire status_rumah on cdb.status_rumah_id=status_rumah.id and status_rumah.type='Status Rumah'
                    LEFT JOIN wtc_questionnaire hobi on cdb.hobi=hobi.id and hobi.type='Hobi'
                    LEFT JOIN wtc_questionnaire gol_darah on cdb.gol_darah=gol_darah.id and gol_darah.type='GolonganDarah'
                    LEFT JOIN wtc_questionnaire penggunaan on cdb.penggunaan_id=penggunaan.id and penggunaan.type='Penggunaan'
                    LEFT JOIN wtc_questionnaire pengguna on cdb.pengguna_id=pengguna.id and pengguna.type='Pengguna'
                    LEFT JOIN wtc_questionnaire merkmotor on cdb.merkmotor_id=merkmotor.id and merkmotor.type='MerkMotor'
                    LEFT JOIN wtc_questionnaire jenismotor on cdb.jenismotor_id=jenismotor.id and jenismotor.type='JenisMotor'
                    where dso.state in ('approved','progress','done') %s
            """ %(query_where)
        cr.execute (query)
        res = cr.fetchall()

        rows = []
        for line in res:
           
        
            kode_dealer       = str(line[0])
            nama_dealer       = str(line[1]) if line[1] != None else ''
            no_faktur         = str(line[2]) if line[2] != None else ''
            date_order        = str(line[3]) if line[3] != None else ''
            engine_no         = str(line[4]) if line[4] != None else ''

            chassis_no        = str(line[5]).replace("MH1", "") if line[5] != None else '' 
            no_polisi         = str(line[6]) if line[6] != None else ''
            tipecolor         = str(line[7]) if line[7] != None else ''
            description       = str(line[8]) if line[8] != None else ''
            no_ktp            = str(line[9]) if line[9] != None else ''
            nama_pembeli      = str(line[10]) if line[10] != None else ''
            birtdate          = str(line[11]) if line[11] != None else ''
            
            no_telp           = str(line[12]) if line[12] != None else ''
            street            = str(line[13]) if line[13] != None else ''
            kode_propinsi     = str(line[14]) if line[14] != None else ''
            propinsi          = str(line[15]) if line[15] != None else ''
            kode_kota         = str(line[16]) if line[16] != None else ''

            kota_kab          = str(line[17]) if line[17] != None else ''
            kode_kec          = str(line[18]) if line[18] != None else ''
            nama_kec          = str(line[19]) if line[19] != None else ''
            zp                = str(line[20]) if line[20] != None else ''
            kelurahan         = str(line[21]) if line[21] != None else ''
            npwp              = str(line[22]) if line[22] != None else ''

            jenis_transaksi   = str(line[23]) if line[23] != None else ''
            amount_total      = str(line[24]) if line[24] != None else ''
            sales_ahm         = str(line[25]) if line[25] != None else ''
            nama_sales        = str(line[26]) if line[26] != None else ''
            jenis_kelamin     = str(line[27]) if line[27] != None else ''
            agama             = str(line[28]) if line[28] != None else ''

            pendidikan        = str(line[29]) if line[29] != None else ''
            pekerjaan         = str(line[30]) if line[30] != None else ''
            pengeluaran       = str(line[31]) if line[31] != None else ''
            jenis_pembelian   = str(line[32]) if line[32] != None else ''
            no_hp             = str(line[33]) if line[33] != None else ''
            email             = str(line[34]) if line[34] != None else ''
            status_hp         = str(line[35]) if line[35] != None else ''

            status_rumah      = str(line[36]) if line[36] != None else ''
            hobi              = str(line[37]) if line[37] != None else ''
            gol_darah         = str(line[38]) if line[38] != None else ''
            dpt_dihubungi     = str(line[39]) if line[39] != None else ''
            kode_customer     = str(line[40]) if line[40] != None else ''
            penggunaan        = str(line[41]) if line[41] != None else ''

            pengguna          = str(line[42]) if line[42] != None else ''
            merk_motor        = str(line[43]) if line[43] != None else ''
            jenis_motor       = str(line[44]) if line[44] != None else ''
     


            h1=kode_dealer+";"+nama_dealer+";"+no_faktur+";"+date_order+";"+engine_no+";"+chassis_no+";"+no_polisi+";"+tipecolor+";"+description+";"+no_ktp+";"+nama_pembeli+";"+birtdate+";"+no_telp+";"+street+";"+kode_propinsi+";"+propinsi+";"+kode_kota+";"+kota_kab+";"+kode_kec+";"+nama_kec+";"+zp+";"+kelurahan+";"+npwp+";"+jenis_transaksi+";"+amount_total+";"+sales_ahm+";"+nama_sales+";"+jenis_kelamin+";"+agama+";"+pendidikan+";"+pekerjaan+";"+pengeluaran+";"+jenis_pembelian+";"+no_hp+";"+email+";"+status_hp+";"+status_rumah+";"+hobi+";"+gol_darah+";"+dpt_dihubungi+";"+kode_customer+";"+penggunaan+";"+pengguna+";"+merk_motor+";"+jenis_motor
            rows.append(list(
                {
                h1
                })
                )
        return rows




    def _get_rows_h23(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids'] 
        # option = data['option']

        query_where = ""

        if branch_ids :
            query_where += " AND wo.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND wo.date >= '%s' " % (start_date)
        if end_date :
            query_where += " AND wo.date <= '%s' "  % (end_date)

        query = """
               select wo.name no_wo,
                wb.code,
                wb.name,
                wb.ahass_code,
                wo.type,
                wo.kpb_ke,
                lot.name engine_no,
                lot.chassis_no,
                wo.no_pol,
                case when pemilik.pekerjaan='pNegeri' then 'Pegawai Negeri'
                when pemilik.pekerjaan='pSwasta' then 'Pegawai Swasta'
                when pemilik.pekerjaan='ojek' then 'Ojek'
                when pemilik.pekerjaan='pedagang' then 'Pedagang'
                when pemilik.pekerjaan='pelajar' then 'Pelajar'
                when pemilik.pekerjaan='guru' then 'Guru'
                when pemilik.pekerjaan='tni' then 'TNI/Polri'
                when pemilik.pekerjaan='irt' then 'Ibu Rumah Tangga'
                when pemilik.pekerjaan='petani/nelayan' then 'Petani/Nelayan'
                when pemilik.pekerjaan='pro' then 'Profesional'
                when pemilik.pekerjaan='lain' then 'Lainnya' end pekerjaan,
                wo.km,
                wo.tanggal_pembelian,
                wo.date,
                pemilik.name Pemilik_stnk,
                pembawa.name pembawa,
                wo.mobile,
                concat(pp.name_template,'-',pav.code)tipecolor,
                pt.description,
                rr.name mekanik,
                hre.sales_ahm,
                hre.nip,
                wol.categ_id,
                pp2.default_code,
                pt2.description,
                wol.price_unit,
                'h23' jenis_transaksi
                from wtc_work_order wo
                LEFT JOIN wtc_branch wb on wo.branch_id=wb.id
                LEFT JOIN stock_production_lot lot on wo.lot_id=lot.id
                LEFT JOIN res_partner pemilik on wo.customer_id=pemilik.id
                LEFT JOIN res_partner pembawa on wo.driver_id=pembawa.id
                LEFT JOIN product_product pp on wo.product_id=pp.id
                LEFT JOIN product_attribute_value_product_product_rel pavpp on pp.id=pavpp.prod_id
                LEFT JOIN product_attribute_value pav on pavpp.att_id=pav.id
                LEFT JOIN product_template pt on pp.product_tmpl_id=pt.id
                LEFT JOIN res_users users on wo.mekanik_id=users.id
                LEFT JOIN resource_resource rr on rr.user_id=users.id
                LEFT JOIN hr_employee hre on rr.id=hre.resource_id
                LEFT JOIN wtc_work_order_line wol on wo.id=wol.work_order_id
                LEFT JOIN product_product pp2 on wol.product_id=pp2.id
                LEFT JOIN product_template pt2 on pp2.product_tmpl_id=pt2.id 
                where wo.state in ('open','approved','finished','done')
                 %s
            """ %(query_where)
        
       
        cr.execute (query)
        ress = cr.fetchall()

        rowsss = []

        for linee in ress:

            no_wo             = str(linee[0]) if linee[0] != None else ''
            code              = str(linee[1]) if linee[1] != None else ''
            name              = str(linee[2]) if linee[2] != None else ''
            ahass_code        = str(linee[3]) if linee[3] != None else ''
            tp                = str(linee[4]) if linee[4] != None else ''

            kpb_ke            = str(linee[5])
            engine_no         = str(linee[6])
            chassis_no        = str(linee[7]).replace("MH1", "") if linee[7] != None else ''
            no_pol            = str(linee[8]) if linee[8] != None else ''
            pekerjaan         = str(linee[9]) if linee[9] != None else ''
            km                = str(linee[10]) if linee[10] != None else ''
            tanggal_pembelian = str(linee[11]) if linee[11] != None else ''
            
            date              = str(linee[12]) if linee[12] != None else ''
            Pemilik_stnk      = str(linee[13]) if linee[13] != None else ''
            pembawa           = str(linee[14]) if linee[14] != None else ''
            mobile            = str(linee[15]) if linee[15] != None else ''
            tipecolor         = str(linee[16]) if linee[16] != None else ''

            dtp               = str(linee[17]) if linee[17] != None else ''
            mekanik           = str(linee[18]) if linee[18] != None else ''
            sales_ahm         = str(linee[19]) if linee[19] != None else ''
            nip               = str(linee[20]) if linee[20] != None else ''
            categ_id          = str(linee[21]) if linee[21] != None else ''
            default_code      = str(linee[22]) if linee[22] != None else ''

            description       = str(linee[23]) if linee[23] != None else ''
            price_unit        = str(linee[24]) if linee[24] != None else ''
            jenis_transaksi   = str(linee[25]) if linee[25] != None else ''
            

            h23=no_wo+";"+code+";"+name+";"+ahass_code+";"+tp+";"+kpb_ke+";"+engine_no+";"+chassis_no+";"+no_pol+";"+pekerjaan+";"+km+";"+tanggal_pembelian+";"+date+";"+Pemilik_stnk+";"+pembawa+";"+mobile+";"+tipecolor+";"+dtp+";"+mekanik+";"+sales_ahm+";"+nip+";"+categ_id+";"+default_code+";"+description+";"+price_unit+";"+jenis_transaksi
            rowsss.append(list(
              {
              h23
              })
              )

        return rowsss

