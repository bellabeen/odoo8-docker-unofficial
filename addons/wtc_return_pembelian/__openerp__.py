{
    "name":"Return Pembelian",
    "version":"1.0",
    "author":"RZ",
    "website":"",
    "category":"TDM",
    "description":"Return Pembelian",
    "depends":["wtc_dealer_menu","wtc_branch","wtc_faktur_pajak","account","wtc_account"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_return_pembelian_view.xml",
        "wtc_return_penjualan_view.xml",
        "wtc_approval_return_pembelian_view.xml",
        "wtc_approval_return_penjualan_view.xml",
        "security/ir.model.access.csv",
        "wtc_branch_config_view.xml",
        'security/res_groups.xml',
        ],
    "active":False,
    "installable":True
}