{
    "name":"Push to Pull",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Push to Pull
    """,
    "depends":["base","wtc_branch","wtc_dealer_menu","wtc_product","wtc_purchase_order","purchase"],
    "init_xml":[],
    "demo_xml":[],
    "data":[  
              'wtc_p2p_purchase_order_report_view.xml',
              'security/ir.model.access.csv',
              'security/ir_rule.xml', 
              "security/res_groups_button.xml",    
              'security/res_groups.xml',              
              'wtc_p2p_config_view.xml',
              'wtc_p2p_product_view.xml',
              'wtc_p2p_periode_view.xml',
              'wtc_p2p_purchase_order_view.xml',
              'wtc_approval_p2p_purchase_view.xml',
              'wtc_p2p_file_upo_view.xml',                                  
#              'data/wtc_approval_config_data.xml',
              ],
    "active":False,
    "installable":True
}
