{
    "name":"Report Stock Distribution",
    "version":"1.0",
    "author":"TEDS",
    "website":"http://teds.tunasdwipamatra.com",
    "category":"TDM",
    "description":"Report Stock Distribution",
    "depends":["base","wtc_branch","wtc_dealer_menu","wtc_stock",],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        'security/ir.model.access.csv',
        "wtc_report_stock_distribution_view.xml",
        "wtc_report_order_fulfillment_view.xml",
        "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
