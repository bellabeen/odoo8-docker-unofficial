{
    "name":"B2B Folder",
    "version":"0.1",
    "author":"RZ",
    "website":"",
    "category":"TDM",
    "description": """
        B2B Folder
    """,
    "depends":["base","mail","wtc_stock"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                "b2b_file_import.xml",
                "b2b_file_fulfillment_view.xml",
                "b2b_configuration_folder_view.xml",
                "b2b_file_view.xml",
                "b2b_file_pmp_wizard.xml",
                'mft_ssu.xml',
                'b2b_file_monitoring_view.xml',
                'report/b2b_file_sl_report_view.xml',
                'security/ir.model.access.csv',
                'security/res_groups.xml',
                'security/res_groups_button.xml',
                'report/b2b_ps_report.xml',
                'report/b2b_ps_report_pivot.xml',
                'data/sheduled_action_psl_status_transfered.xml'
                  ],
    "active":False,
    "installable":True
}
