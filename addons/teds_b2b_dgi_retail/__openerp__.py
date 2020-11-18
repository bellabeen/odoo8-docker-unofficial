{
    'name':"TEDS B2B DGI Retail",
    'version':'10.0.1.0.0',
    'depends':['base_suspend_security','teds_b2b_api_configuration','wtc_branch','teds_lead','dealer_sale_order','wtc_hr_employee','wtc_work_order'],
    'author':"TDM",
    'website':"www.honda-ku.com",
    'category':"TEDS",
    'description':"""TEDS B2B DGI Retail""",
    'data': [
        "views/teds_b2b_api_config_view.xml",
        "views/teds_b2b_dgi_error_view.xml",
        "views/teds_lead_view.xml",
        "views/teds_spk_view.xml",
        "views/teds_employee_view.xml",
        "views/teds_work_order_view.xml",
        "views/teds_product_view.xml",
        "views/teds_b2b_dgi_mapping_master_jasa.xml",
    ],
}