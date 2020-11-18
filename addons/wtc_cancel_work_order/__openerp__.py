{
    "name":"Work Order Cancellation",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Work Order Cancellation",
    "depends":["wtc_work_order","wtc_account_voucher","wtc_stock","wtc_cancellation"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_work_order_cancel_view.xml",
        "wtc_branch_config_view.xml",
        'report/teds_work_order_cancel.xml',
        'report/teds_work_order_cancel_print.xml',

        "data/wtc_branch_config.xml",
        "security/res_groups.xml",
        "security/res_groups_button.xml",
        ],
    "active":False,
    "installable":True
}