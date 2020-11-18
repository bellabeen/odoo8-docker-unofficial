{
    "name":"Kwitansi",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Kwitansi",
    "depends":["base","account_voucher","account","wtc_branch","wtc_account_voucher"],
    "init_xml":[],
    "demo_xml":[],
    "data":["wtc_kwitansi_report.xml","wtc_kwitansi_view.xml","wtc_cancel_kwitansi_view.xml",
            'security/ir_rule.xml',
            'security/ir.model.access.csv',
            'security/res_groups.xml',
            ],
    "active":False,
    "installable":True
}