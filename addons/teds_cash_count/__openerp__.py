{
    "name":"Teds Cash Count",
    "version":"0.1",
    "author":"TDM",
    "category":"TDM",
    "description": """
        Teds Cash Count by Sistem
    """,
    "depends":['wtc_branch','wtc_pettycash'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "data/data_validasi.xml",
        "views/teds_branch_view.xml",
        "views/teds_cash_count_validasi_view.xml",
        "views/teds_cash_count_view.xml",
        "report/teds_cash_count_berita_acara_wizard.xml",
        "report/teds_laporan_cash_count_wizard.xml",
        
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "security/res_group_button.xml",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
