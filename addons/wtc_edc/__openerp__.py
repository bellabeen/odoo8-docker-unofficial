{
    "name":"Payment Method EDC",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        EDC
    """,
    "depends":["base","account_voucher","account"],
    "init_xml":[],
    "demo_xml":[],
    "data":[  
            'security/ir.model.access.csv',
            'security/ir_rule.xml',
            'security/res_groups_button.xml', 
            "wtc_edc_view.xml",
            "wtc_branch_config_view.xml",
            "wtc_disbursement_view.xml",
            "wtc_cancel_disbursement_view.xml",

            'report/teds_disbursement_cancel.xml',
            'report/teds_disbursement_cancel_print.xml',

            'data/wtc_branch_config.xml',
            'security/res_groups.xml',            

#             'data/res_partner_bank.xml',   
#             'data/edc.xml',      

              ],
    "active":False,
    "installable":True
}