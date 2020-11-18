{
    "name":"Teds Stock Opname Asset",
    "version":"0.1",
    "author":"TDM",
    "category":"TDM",
    "description": """
        Teds Stock Opname Asset.
    """,
    "depends":['teds_stock_opname','wtc_purchase_asset'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "data/pic_data.xml",
        "views/teds_stock_opname_asset_view.xml",
        "views/teds_stock_opname_asset_pic_view.xml",
        "report/teds_stock_opname_asset_print_validasi.xml",
        "report/teds_stock_opname_asset_print_bakso.xml",

        # "report/teds_laporan_stock_opname_wizard.xml",
        
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "security/res_group_button.xml",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
