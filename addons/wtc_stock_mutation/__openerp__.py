{
    "name":"Stock Mutation",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description":"Stock Mutation",
    "depends":["base","wtc_branch","wtc_dealer_menu","wtc_approval","wtc_purchase_order","teds_double_pricelist_so"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "wtc_mutation_request_view.xml",
            "wtc_stock_distribution_view.xml",
            "wtc_mutation_order_view.xml",
            "wtc_approval_stock_mutation_view.xml",
            "wtc_approval_stock_distribution_view.xml",
            "wtc_mutation_request_workflow.xml",
#             "wtc_stock_distribution_workflow.xml",
#             "wtc_mutation_order_workflow.xml",
            "security/ir.model.access.csv",
            "security/ir_rule.xml",
            "security/res_groups.xml",
            "security/res_groups_button.xml",
            'data/wtc_approval_config_data.xml'
            ],
    "active":False,
    "installable":True
}