{
    "name":"Debit/Credit Note",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Debit/Credit Note",
    "depends":["base","wtc_account_voucher","wtc_kwitansi","wtc_branch","wtc_faktur_pajak","wtc_account_move","account","teds_payment_request_type"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                    "wtc_payment_request_report.xml",
                    "wtc_dn_nc_view.xml",
                    "wtc_other_receivable_view.xml",
                    "wtc_register_kwitansi_view.xml",
                    "report/teds_payments_request_report.xml",
                    "security/ir_rule.xml",
                    "security/ir.model.access.csv",
                    "security/res_groups.xml",
                    "security/res_group_button.xml",
                    "data/wtc_approval_config_data.xml",
                    
                  ],
    "active":False,
    "installable":True
}
