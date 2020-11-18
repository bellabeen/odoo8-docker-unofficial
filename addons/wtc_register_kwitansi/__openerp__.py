{
    "name":"Registrasi Kwitansi",
    "version":"1.0",
    "author":"ABK",
    "category":"TDM",
    "description": """
        Register Kwitansi
    """,
    "depends":["base","wtc_branch","wtc_sequence"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                  "wtc_register_kwitansi_view.xml",
                  "wtc_generate_register_kwitansi_view.xml",
                  'security/ir.model.access.csv',
                  'security/res_groups.xml'
                 ],
    "active":False,
    "installable":True
}
