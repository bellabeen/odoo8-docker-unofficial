{
    "name":"Teds Branch Config Location",
    "version":"0.1",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Config location untuk data purchase order
    """,
    "depends":["wtc_branch","wtc_purchase_order","wtc_stock"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "views/teds_branch_location_config_view.xml",
            "views/teds_stock_packing_view.xml",
            
            "security/ir.model.access.csv",
            "security/res_groups.xml",
        ],
    "active":False,
    "installable":True
}
