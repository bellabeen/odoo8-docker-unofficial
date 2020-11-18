{
    "name":"WTC Program Subsidi",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        Custom Field
    """,
    "depends":["base","sale","wtc_branch","wtc_approval"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
              "wtc_program_subsidi_view.xml",
              "wtc_subsidi_barang_view.xml",
              "wtc_approval_program_subsidi_view.xml",
              "wtc_approval_subsidi_barang_view.xml",
              "wtc_hutang_komisi_view.xml",
              "wtc_approval_hutang_komisi_view.xml",
              'security/ir.model.access.csv',
              'data/wtc_approval_config_data.xml',
              'security/res_groups.xml',
              ],
    "active":False,
    "installable":True
}