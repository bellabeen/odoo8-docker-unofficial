{
    'name':"TEDS Payment Requests Type",
    'version':'1.0',
    'depends':["wtc_account_voucher"],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""TEDS Payment Requests Type""",
    'demo':[],
    'data':[
        "views/teds_payment_request_type_view.xml",
        "views/teds_petty_cash_type_view.xml",
        
        "security/res_groups.xml",
        "security/ir.model.access.csv",
    ],
}