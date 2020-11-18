{
    "name":"Advance Payment",
    "version":"1.0",
    "author":"ABK",
    "email":"anggar.bagus@gmail.com",
    "category":"TDM",
    "description": """
        Advance Payment
    """,
    "depends":["base","account","wtc_branch","wtc_approval","wtc_dealer_menu","wtc_account_filter"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_advance_payment_report.xml",
        "report/teds_advance_payment_draft_report_view.xml",
        "wtc_advance_payment_view.xml",
        "wtc_approval_advance_payment_view.xml",
        "wtc_settlement_view.xml",
        "wtc_approval_settlement_view.xml",
        "wtc_advance_payment_workflow.xml",
        "wtc_settlement_workflow.xml",
        "wtc_branch_config_view.xml",
        "security/ir.model.access.csv",
        "data/wtc_approval_config_data.xml",
        "security/res_groups.xml",
        "views/wtc_settlement_report_done.xml",
        "views/wtc_settlement_report_draft.xml"
    ],
    "active":False,
    "installable":True
}
