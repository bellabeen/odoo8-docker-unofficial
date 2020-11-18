{
    "name":"Teds Report Mekanik Mitra",
    "version":"0.1",
    "author":"DM",
    "website":"teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Report Mekanik Mitra
    """,
    "depends":["wtc_work_order"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "views/teds_master_mekanik_mitra.xml",
        "views/teds_matrix_mekanik_mitra.xml",
        "views/teds_mekanik_mitra_absensi.xml",
        "report/teds_report_mekanik_mitra.xml",

        "security/ir.model.access.csv",
        "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
