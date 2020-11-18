{
    "name":"Teds Stock Opname",
    "version":"0.1",
    "author":"TDM",
    "category":"TDM",
    "description": """
        Teds Stock Opname.
    """,
    "depends":['wtc_proses_stnk'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "views/teds_stock_opname_menu_view.xml",
        "views/teds_stock_opname_stnk_view.xml",
        "report/teds_stock_opname_stnk_pint_validasi.xml",
        "report/teds_stock_opname_stnk_pint_bakso.xml",

        "views/teds_stock_opname_bpkb_view.xml",
        "report/teds_stock_opname_bpkb_pint_validasi.xml",
        "report/teds_stock_opname_bpkb_pint_bakso.xml",
        "report/teds_laporan_stock_opname_wizard.xml",
        
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "security/res_group_button.xml",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
