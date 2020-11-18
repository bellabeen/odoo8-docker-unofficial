{
    "name":"Custom Account",
    "version":"0.1",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Custom field account.
    """,
    "depends":["base", "account","wtc_branch","analytic","account_payment",'procurement'],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                  "account_view.xml",
                  "wtc_procurement_view.xml",
                  "wtc_payment_order_view.xml",
                  "security/res_groups.xml",
                  "security/res_groups_button.xml",
                  "supplier_invoice_view.xml",
                  ],
    "active":False,
    "installable":True
}
