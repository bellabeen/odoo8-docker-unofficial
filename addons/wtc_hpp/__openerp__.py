{
    "name":"Harga Pokok Penjualan",
    "version":"0.1",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        HPP with Serial Number.
    """,
    "depends":["base", "stock", "account", "purchase"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "hpp_view.xml",
            'security/ir.model.access.csv',
            'security/res_groups.xml',
            'security/res_groups_button.xml',
            ],
    "active":False,
    "installable":True
}
