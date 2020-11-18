{
    "name":"Purchase Order for Asset",
    "version":"0.1",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Purchase Order for Asset With Depreciation.
    """,
    "depends":["base", "wtc_purchase_requisition","wtc_account_voucher","purchase", "account", "account_asset", "wtc_dealer_menu","wtc_account"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                    'data/account_journal.xml',
                    'data/wtc_approval_config_data.xml',
                    'data/wtc.branch.config.xml',
                    'wtc_branch_config_view.xml',
                    'security/ir.model.access.csv',
                    'security/ir_rule.xml',
                    "asset_view.xml",
                    "prepaid_view.xml",
                    "receipt_asset_view.xml",
                    "wtc_purchase_asset_view.xml",
                    "wtc_asset_adjustment_view.xml",
                    "wtc_disposal_asset_view.xml",
                    "views/teds_master_lokasi_view.xml",
                    
                    'report/teds_disposal_asset_print_wizard.xml',
                    'security/res_groups.xml', 
                    'security/res_groups_button.xml', 
                  ],
    "active":False,
    "installable":True
}
