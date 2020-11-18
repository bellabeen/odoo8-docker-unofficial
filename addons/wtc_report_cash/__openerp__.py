{
    "name":"Report Cash",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Report Cash",
    "depends":["base","wtc_branch","wtc_account_move","wtc_account_journal","wtc_bank_transfer"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_report_cash.xml",
        "security/res_groups.xml",
        "view/wtc_report_non.xml",
        "view/wtc_report_pettycash_pdf.xml",
        #"wtc_report_cash_view.xml"
    ],
    "active":False,
    "installable":True
}
