{
    'name':"TEDS MUTASI ASSET",
    'version':'1.0',
    'depends':["base_suspend_security","web_readonly_bypass","wtc_branch","wtc_purchase_asset"],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""TEDS MUTASI ASSET""",
    'demo':[],
    'data':[
        'views/teds_mutation_request_asset_view.xml',
        'views/teds_mutation_asset_view.xml',

        'report/teds_mutasi_asset_berita_acara_print.xml',

        'security/res_groups.xml',
        'security/res_groups_button.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
}