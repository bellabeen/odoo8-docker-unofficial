{
    "name":"Teds Report Weekly",
    "version":"0.1",
    "author":"TDM",
    "category":"TDM",
    "description": """
        Teds Report Weekly.
    """,
    "depends":['wtc_branch','wtc_hr_employee','dealer_sale_order'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "data/ir_cron.xml",

        "views/teds_master_area_view.xml",
        "views/teds_master_main_dealer_view.xml",
        "views/teds_konsolidate_weekly_view.xml",
        "report/teds_konsolidate_weekly_repot_wizard.xml",

        "security/res_groups.xml",
        "security/res_groups_button.xml",
    ],
    "active":False,
    "installable":True,
    'external_dependencies' : {
        'python' : ['numpy'],
    }
}
