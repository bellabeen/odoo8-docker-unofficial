{
    "name":"Cancellation",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Cancellation",
    "depends":["dealer_sale_order","wtc_account_voucher","wtc_stock","wtc_stock_mutation","wtc_dn_nc"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_cancellation_view.xml",
        "wtc_branch_config_view.xml",
#         "wtc_update_lot_view.xml",
        "data/wtc.branch.config.xml",
        'report/teds_cancellation_print.xml',
        'report/teds_dealer_sale_order_cancel_print.xml',
        'report/teds_payment_cancel_print.xml',
        'report/teds_mutation_cancel_print.xml',


        "security/res_groups.xml",
        "security/res_groups_button.xml",
        ],
    "active":False,
    "installable":True
}