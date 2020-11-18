{
    "name":"Interface EPICOR",
    "version":"1.0",
    "author":"TEDS",
    "website":"",
    "category":"TDM",
    "description": """
        File Interface to EPICOR - FICO
    """,
    "depends":["base","account"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        'views/teds_epicor_config_path_view.xml',        
        'views/teds_interface_epicor_view.xml',
        'views/teds_interface_epicor_wizard.xml',
        # 'data/teds_interface_epicor_scheudled.xml',
        'security/res_groups.xml',
    ],
    "active":False,
    "installable":True
}
