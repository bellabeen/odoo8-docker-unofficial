{
    "name":"Pengurusan STNK dan BPKB",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Permohonan Faktur
    """,
    "depends":["base","account","stock","wtc_dealer_menu","wtc_serial_number","product"],
    "init_xml":[],
    "demo_xml":[],
    "data":[  
              'security/ir.model.access.csv',
              'security/ir_rule.xml',    
              'security/res_groups.xml',
              'security/res_groups_button.xml',            
              "wtc_pengurusan_stnk_bpkb_workflow.xml",
              "wtc_pengurusan_sntk_bpkb_view.xml",
              "wtc_serial_number_pf_view.xml",
              "wtc_branch_config_view.xml",
#               'data/wtc.branch.config.xml'          
              ],
    "active":False,
    "installable":True
}