{
    'name':"TEDS API Work Order",
    'version':'1.0',
    'depends':['base_suspend_security','wtc_work_order','teds_api_configuration','wtc_hr_employee'],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""TEDS API Work Order""",
    'demo':[],
    'data':[        
        'views/teds_api_work_order_view.xml',
        'views/teds_hr_employee_view.xml',
        'views/teds_api_master_bundling_view.xml',
        'views/teds_work_order_view.xml',
        'data/teds_api_work_order_bundling_cron.xml',
        'reports/teds_api_log_work_order_report_view.xml',
        'security/res_groups.xml',
    ],
}