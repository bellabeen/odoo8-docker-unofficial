{
    "name":"AHM Interface",
    "version":"1.0",
    "author":"RZ",
    "website":"",
    "category":"TDM",
    "description": """
        SAL, STO, POD
    """,
    "depends":["base"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
              "wtc_ahm_sal_view.xml",
              "wtc_ahm_sto_view.xml",
              "wtc_ahm_pod_view.xml",
              "wtc_ahm_rec_view.xml",
	           'security/ir.model.access.csv',
              'security/res_groups.xml', 
              ],
    "active":False,
    "installable":True
}
