{
    "name":"Closing Fiscal Year by Branch",
    "version":"0.1",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Closing Fiscal Year by Branch.
        - Closing Profit & Loss to Retained Erning
        - Transfer Balance to New Fiscal Year
    """,
    "depends":["base", "account", "wtc_branch", "wtc_sequence", "wtc_dealer_menu"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "wizard/teds_fiscalyear_close_views.xml",
            "security/res_groups.xml",
        ],
    "active":False,
    "installable":True
}
