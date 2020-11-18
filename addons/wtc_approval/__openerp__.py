{
    "name":"WTC Approval Bertingkat",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
    """,
    "depends":["base","wtc_branch","mail","wtc_dealer_menu"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_approval_view.xml",
        "wtc_approval_config_view.xml",
        "wtc_so_approval_view.xml",
        'reports/wtc_matrix_approval_report.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/res_groups.xml',
        'wtc_copy_approval_view.xml'
        ],
    "active":False,
    "installable":True
}