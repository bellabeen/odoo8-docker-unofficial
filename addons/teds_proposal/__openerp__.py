{
    'name': 'TEDS Proposal',
    'version': '1.0',
    'depends': [
        'base',
        'base_suspend_security',
        'report',
        'report_custom_filename',
        'wtc_dealer_menu',
        'teds_config_files',
        'web_readonly_bypass',
        'wtc_branch',
        'wtc_approval',
        'wtc_dn_nc',
        'wtc_advance_payment'
    ],
    'author': 'FAL',
    'category': 'Custom Modules',
    'summary': 'Proposal Online',
    'description': """
        Modul yang mengelola pengajuan proposal dana.
    """,
    'demo': [],
    'data': [
        'views/teds_proposal_view.xml',
        'views/wtc_dn_nc_view.xml',
        'views/wtc_advance_payment_view.xml',
        'reports/teds_proposal_print_view.xml',
        'reports/teds_payment_request_report.xml',
        'reports/teds_advance_payment_draft_report.xml',
        'data/res_groups.xml',
        'data/wtc_approval_config_data.xml',
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'security/res_groups_button.xml'
    ],
}