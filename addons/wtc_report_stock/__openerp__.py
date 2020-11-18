{
    "name":"Report Stock UNit",
    "version":"1.0",
    "author":"rz",
    "website":"",
    "category":"TDM",
    "description":"Report Stock Unit",
    "depends":["base","base_setup","stock","wtc_dealer_menu","wtc_branch","wtc_sale_order"],
    "init_xml":[],
    "demo_xml":[],
    
    "data":[
        'views/wtc_report_stock_view.xml',
        'wtc_stock_report_tree.xml',
        "wtc_report_stock_unit_wizard.xml",
        "wtc_report_stock_sparepart_wizard.xml",
        "wtc_report_stock_accesories_wizard.xml",
        "wtc_report_stock_direct_gift_view.xml",
        'security/res_groups.xml',
        ],
   'qweb' : [
        "static/src/xml/wtc_report_stock_tree.xml"
    ],
    "active":False,
    "installable":True
}
