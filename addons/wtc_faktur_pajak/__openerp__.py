{
    "name":"Faktur Pajak",
    "version":"1.0",
    "author":"PT.Witaco",
    "category":"TDM",
    "description": """
        Generate Faktur Pajak
    """,
    "depends":["base","wtc_branch","wtc_sequence","wtc_dealer_menu","wtc_register_kwitansi"],
    "init_xml":[],
    "demo_xml":[],
    "data":[        
                  'security/ir.model.access.csv',
                  'data/wtc_remark_data.xml',
                  'data/wtc_signature_data.xml',
                  "wtc_faktur_pajak_report.xml",
                  "report/wtc_faktur_pajak_report.rml",
                  "wtc_faktur_pajak_view.xml",
                  "wtc_signature_view.xml",
                  "wtc_remark_view.xml",
                  "wtc_generate_faktur_pajak_view.xml",
                  "wtc_faktur_pajak_gabungan_view.xml",
                  "wtc_faktur_pajak_other_view.xml",
                  "wtc_regenerate_faktur_pajak_view.xml",
		              'security/res_groups.xml',
                  'security/res_groups_button.xml',
                  "views/wtc_faktur_pajak_gabungan_report.xml"

                 ],
    "active":False,
    "installable":True
}
