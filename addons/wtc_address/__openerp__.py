{
    "name":"Addresses",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        Master Province, City, Kecamatan, Keluarahan
    """,
    "depends":["base"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
              "wtc_city_view.xml",
              "wtc_kecamatan_view.xml",
              "wtc_kelurahan_view.xml",
            "res.country.state.csv",
            "wtc.city.csv",
            "wtc.kecamatan.csv",
              #"wtc.kelurahan.csv",
              'security/ir.model.access.csv',
#               'data/res.country.state.xml',
#               'data/wtc.city.xml',
#               'data/wtc.kecamatan.xml'
              ],
    "active":False,
    "installable":True
}
