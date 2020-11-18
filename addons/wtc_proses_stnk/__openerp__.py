{
    "name":"Proses STNK",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Permohonan Faktur
    """,
    "depends":["base","account","wtc_branch","stock","wtc_dealer_menu","wtc_serial_number","wtc_approval"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            'data/wtc_approval_config_data.xml',
        
            "wtc_proses_stnk_report.xml",
            "wtc_proses_birojasa_workflow.xml",                              
            "wtc_approval_proses_birojasa_workflow.xml",
            "wtc_generate_stnk_bpkb_view.xml",
            "wtc_lokasi_bpkb_view.xml",
            "wtc_lokasi_stnk_view.xml",
            "wtc_proses_stnk_view.xml",
            "wtc_penerimaan_stnk_view.xml",
            "wtc_penerimaan_bpkb_view.xml",
            "wtc_proses_birojasa_view.xml",
            "wtc_approval_proses_birojasa_view.xml",
            "wtc_mutasi_bpkb_view.xml",
            "wtc_mutasi_stnk_view.xml",
            "wtc_serial_number_pf_view.xml",
            "wtc_branch_config_view.xml",
            "wtc_cancel_proses_stnk_view.xml",
            "wtc_cancel_penerimaan_stnk_view.xml",
            "wtc_cancel_penerimaan_bpkb_view.xml",            
            'views/wtc_penerimaan_bpkb_report.xml',
            'views/wtc_mutasi_stnk_report.xml',
            'views/wtc_mutasi_bpkb_report.xml',
                        
#             'data/wtc.branch.config.xml',
#             'data/ir.sequence.xml' 
            'wtc_pajak_progressive_view.xml',  
            'security/res_groups.xml',                                         
            'security/res_groups_button.xml', 
            'security/ir.model.access.csv',
            'security/ir_rule.xml', 
              ],
    "active":False,
    "installable":True
}