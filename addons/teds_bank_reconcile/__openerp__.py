{
    "name":"TEDS BANK RECONCILE",
    "version":"0.1",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        TEDS BANK RECONCILE
    """,
    "depends":["base","wtc_dealer_menu","account","wtc_branch"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "views/teds_bank_mutasi_view.xml",
            "views/teds_bank_reconcile_view.xml",
            "views/teds_bank_reconcile_cancel_view.xml",

            "data/auto_reconcile.xml",
            "report/teds_bank_reconcile_report_view.xml",
            "report/export_bank_mutasi_view.xml",
            "security/ir.model.access.csv",
            "security/res_groups.xml",
            "security/res_groups_button.xml",
            "security/ir_rule.xml",
        ],
    "active":False,
    "installable":True
}
