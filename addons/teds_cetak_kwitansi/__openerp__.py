{
    "name":"Teds Cetak Kwitansi",
    "version":"0.1",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Teds Cetak Kwitansi
    """,
    "depends":["wtc_branch","wtc_sequence"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "views/teds_cetak_kwitansi_view.xml",
        "report/teds_cetak_kwitansi_print_view.xml",
        "report/teds_laporan_cetak_kwitansi.xml",
        
        "security/res_groups.xml",
        "security/res_groups_button.xml",
    ],
    "active":False,
    "installable":True
}