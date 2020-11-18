{
    "name":"Collecting / Bulking Move Lines",
    "version":"0.1",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Collecting / Bulking Move Line Receivables / Payables.
    """,
    "depends":["base", "account", "wtc_branch", "wtc_sequence", "wtc_dealer_menu","wtc_approval"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "views/teds_collecting_views.xml",
            "views/teds_collecting_cancel_views.xml",
            "views/wtc_branch_config_views.xml",
            "security/ir.model.access.csv",
            "security/res_groups.xml",
            "security/res_groups_action.xml",
        ],
    "active":False,
    "installable":True
}
