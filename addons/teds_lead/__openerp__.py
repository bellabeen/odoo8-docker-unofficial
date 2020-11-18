{
    "name":"Teds Lead Management",
    "version":"1.0",
    "author":"TEDS",
    "website":"",
    "category":"TDM",
    "description": """
        Teds Leads
    """,
    "depends":["dealer_sale_order","teds_sales_activity_plan_btl"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "data/teds_stage_data.xml",
        
        "views/teds_lead_stage_view.xml",
        "views/teds_lead_view.xml",
        "views/teds_lead_master_result_activity_view.xml",
        "views/teds_lead_activity_view.xml",
        "views/res_partner_view.xml",
        "views/teds_branch_view.xml",

        "reports/teds_lead_report_view.xml",
        
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
