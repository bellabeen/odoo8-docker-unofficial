{
    "name":"Teds Stock Opname Direct Gift",
    "version":"0.1",
    "author":"TDM",
    "category":"TDM",
    "description": """
        Teds Stock Opname Direct Gift.
    """,
    "depends":['teds_stock_opname','wtc_stock'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "views/teds_stock_opname_direct_gift_view.xml",
        "report/teds_stock_opname_dg_print_validasi.xml",
        "report/teds_stock_opname_dg_print_bakso.xml",
        
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "security/ir_rule.xml",
        "security/res_group_button.xml",
    ],
    "active":False,
    "installable":True
}
