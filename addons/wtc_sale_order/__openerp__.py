{
    "name":"MD Sale Order",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        Main Dealer Sale Order
    """,
    "depends":["base","product","wtc_branch","account","wtc_serial_number","account","account_voucher","wtc_stock_mutation","teds_double_pricelist_so"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
              "wtc_generate_df_view.xml",
              "wtc_sale_order_report_view.xml",
              "wtc_sale_order_workflow.xml",
              "teds_approval_so_workflow.xml",
              "teds_approval_so_view.xml",
              "data/wtc_branch_config.xml",
              "res_partner_view.xml",
              "wtc_sale_order_view.xml",
              "wtc_branch_config_view.xml",
              "security/res_groups.xml",
              "security/res_groups_button.xml",
              ],
    "active":False,
    "installable":True
}