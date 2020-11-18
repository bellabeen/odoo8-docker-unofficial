{
    'name':"TEDS API Configuration",
    'version':'10.0.1.0.0',
    'depends':['wtc_branch'],
    'author':"TDM",
    'website':"www.honda-ku.com",
    'category':"TEDS",
    'description':"""TEDS API Configuration""",
    'data': [
        'views/teds_api_configuration_view.xml',
        'views/teds_api_log_view.xml',
        'views/teds_api_button_auto_view.xml',
        'views/teds_api_manual_execute_view.xml',
        'data/teds_api_button_view.xml',
        'views/teds_api_list_partner_view.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
    ],
}