{
    "name":"Penyerahan STNK dan BPKB",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Penyerahan STNK dan BPKB
    """,
    "depends":["base","wtc_branch","stock","wtc_dealer_menu","wtc_serial_number","wtc_jumlah_cetak","wtc_proses_stnk"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            'security/ir.model.access.csv',
            'security/ir_rule.xml',
            "wtc_penyerahan_stnk_report.xml",
            "wtc_penyerahan_stnk_view.xml",
            "wtc_penyerahan_bpkb_view.xml",
            "wtc_serial_number_pf_view.xml",
            "wtc_cancel_penyerahan_bpbk_view.xml",
            "wtc_cancel_penyerahan_stnk_view.xml",

            'report/teds_penyerahan_stnk_cancel.xml',
            'report/teds_penyerahan_stnk_cancel_print.xml',
            'report/teds_penyerahan_bpkb_cancel_print.xml',
            
            'security/res_groups.xml',
            'security/res_groups_button.xml',
              ],
    "active":False,
    "installable":True
}