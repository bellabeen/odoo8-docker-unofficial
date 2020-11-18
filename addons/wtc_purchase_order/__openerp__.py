{
    "name":"Purchase Order",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Purchase Order",
    "depends":["base","purchase","wtc_branch","wtc_account_voucher","wtc_approval","wtc_sequence","wtc_close_purchase","wtc_dealer_menu","wtc_account"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "wtc_purchase_order_report.xml",
            "wtc_purchase_order_view.xml",
            "wtc_approval_po_view.xml",
            "wtc_approval_po_workflow.xml",
            "wtc_purchase_order_type_view.xml",
            "wtc_branch_config_view.xml",
            "wtc_purchase_order_type_data.xml",
            "wtc_account_invoice_view.xml",
            "wtc_on_incoming_shipments_showroom.xml",
            "wtc_purchase_order_workflow.xml",
            'security/ir.model.access.csv',
            'security/ir_rule.xml',
            'security/res_groups.xml',
            'security/res_groups_button.xml',
#             'data/ir.sequence.xml',
#             'data/wtc.branch.config.xml'
            'data/wtc_approval_config_data.xml',
            ],

    "active":False,
    "installable":True
}