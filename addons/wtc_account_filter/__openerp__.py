{
    "name":"Account FILTER",
    "version":"1.0",
    "author":"Riki Zubri",
    "email":"rikizubri26@gmail.com",
    "category":"TDM",
    "description": """
        Account Filter
    """,
    "depends":["base","account","wtc_branch","wtc_dealer_menu"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
              "wtc_account_filter_view.xml",
              'security/ir.model.access.csv',
              'security/res_groups.xml',
              ],
    "active":False,
    "installable":True
}
