{
    "name":"Net Off",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Net Off",
    "depends":["base","account","wtc_branch","wtc_account_move","wtc_eksport_import"],
    "init_xml":[],
    "demo_xml":[],
    "data":[                
                'wtc_net_off_view.xml',
                'security/res_groups.xml',
                'security/res_groups_button.xml',   
                'wtc_approval_net_off_view.xml',                             
                'security/ir_rule.xml',
                'security/ir.model.access.csv',
                'data/wtc_approval_config_data.xml',
                  ],
    "active":False,
    "installable":True
}
