{
    "name":"CDDB",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        CDDB
    """,
    "depends":["base","account","wtc_res_partner","sales_team"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "wtc_questionnaire_view.xml",
            "wtc_res_partner_cddb_view.xml",
            "wtc_res_partner_wizard_view.xml",
            "wtc_res_partner_data.xml",
            'security/ir.model.access.csv',
            "wtc_sales_team.xml",
            "wtc_partner_customer_view.xml",
            "wtc_partner_finco_view.xml",
            "wtc_res_partner_kanban_view.xml",
            'security/res_groups.xml',
            ],
    "active":False,
    "installable":True
}