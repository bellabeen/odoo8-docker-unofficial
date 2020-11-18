{
    'name':"TEDS B2B API Configuration",
    'version':'10.0.1.0.0',
    'depends':['wtc_branch'],
    'author':"TDM",
    'website':"www.honda-ku.com",
    'category':"TEDS",
    'description':"""TEDS B2B API Configuration""",
    'data': [
        "views/teds_b2b_api_schedule.xml",
        "views/teds_b2b_api_config.xml",
        "views/teds_b2b_api_url.xml",
        "views/teds_b2b_api_log.xml",

        "security/ir.model.access.csv",
        "security/res_groups.xml"
    ],
}