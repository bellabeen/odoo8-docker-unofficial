{
    'name':"TEDS PART HOTLINE",
    'version':'1.0',
    'depends':["wtc_work_order","wtc_cancel_work_order","wtc_account_move","wtc_approval","wtc_stock","wtc_stock_mutation","teds_branch_config_location"],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""TEDS PART HOTLINE""",
    'demo':[],
    'data':[
        'views/teds_part_hotline_view.xml',
        'views/teds_purchase_order_view.xml',
        'views/teds_work_order_view.xml',
        'views/teds_stock_packing_view.xml',
        'views/teds_part_hotline_cancel_view.xml',
        
        'report/teds_part_hotline_monitoring_view.xml',
        'report/teds_part_hotline_print.xml',
        'report/teds_laporan_part_hotline.xml',
        
        'security/res_groups.xml',
        'security/res_groups_button.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
}