{
    "name":"Cancel Tagihan Birojasa",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Cancellation",
    "depends":["wtc_proses_stnk","base","account","wtc_cancellation"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wtc_cancel_birojasa_view.xml",
        "wtc_branch_config_view.xml",
        "wtc_cancel_pajak_progressive_view.xml",
        # "data/wtc.branch.config.xml",
        "security/res_groups.xml",
        "security/res_groups_button.xml",
        ],
    "active":False,
    "installable":True
}
