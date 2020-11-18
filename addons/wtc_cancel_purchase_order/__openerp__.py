{
    "name":"Purchase Order Cancellation",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Purchase Order Cancellation",
    "depends":["purchase","base","account","wtc_cancellation","wtc_hpp","stock","wtc_cancellation"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_cancel_purchase_order_view.xml",
        "wtc_branch_config_view.xml",

        'report/teds_purchase_cancel_form.xml',
        'report/teds_purchase_cancel_print.xml',

        "data/wtc.branch.config.xml",
        "security/res_groups.xml",
        "security/res_groups_button.xml",
        ],
    "active":False,
    "installable":True
}