{
    "name":"addons res partner",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        Membuat Tambahan Master Principle, Biro Jasa, Forwarder, General Supplier, 
        Dealer, Finance Company, Customer di res_partner
    """,
    "depends":["base","hr","wtc_address","wtc_branch","product","sale","purchase"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            'wtc_request_platform_view.xml',                        
            'security/ir.model.access.csv',
            'security/res_groups.xml',
            "security/res_groups_button.xml",                        
            "data/wtc_approval_config_data.xml",
            "wtc_res_partner_view.xml",
            "wtc_request_payment_term.xml",
            'wtc_approval_rpt_view.xml',
            'wtc_approval_platform_view.xml',
            'security/ir_rule.xml',
#            "wtc_res_partner_incentive_view.xml",
#             'data/finco.xml',
#             'data/wtc.incentive.finco.line.detail.xml'
            ],
    "active":False,
    "installable":True
}