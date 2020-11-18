{
    'name': 'TEDS Master Activity Budget',
    'version': '1.0',
    'depends': ['base','web_readonly_bypass','hr','wtc_dealer_menu','wtc_branch'],
    'author': 'FAL',
    'category': 'Custom Modules',
    'summary': 'Master Activity Budget',
    'description': """
        Master yang memuat budget aktivitas tiap departemen per tahun (tanpa nominal).
    """,
    'demo': [],
    'data': [
        'views/hr_department_view.xml',
        'views/teds_master_act_budget_view.xml',
        'security/ir.model.access.csv',
        'security/res_groups.xml'
    ],
}