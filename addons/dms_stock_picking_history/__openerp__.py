{
    'name':"DMS Stock Picking History",
    'version':'1.0',
    'depends':['wtc_stock','teds_api_configuration'],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""DMS Stock Picking History""",
    'demo':[],
    'data':[        
        'data/scheduled_actions.xml',
    	'views/dms_stock_picking_history_view.xml',

        'security/ir.model.access.csv',
        'security/res_groups.xml',
    ],
}