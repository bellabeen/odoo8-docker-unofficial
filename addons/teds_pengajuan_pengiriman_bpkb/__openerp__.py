{
    'name':"TEDS Pengajuan Pengiriman BPKB",
    'version':'1.0',
    'depends':["wtc_proses_stnk"],
    'author':"TDM",
    'website':"",
    'category':'Custom Modules',
    'description':"""TEDS Pengajuan Pengiriman BPKB""",
    'demo':[],
    'data':[
        "views/teds_pengiriman_bpkb_view.xml",
        "report/teds_pengiriman_bpkb_print.xml",

        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "security/res_group_button.xml",
    ],
}