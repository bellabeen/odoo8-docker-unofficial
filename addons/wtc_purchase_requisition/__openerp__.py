{
    "name":"Purchase Request",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"www.witaco.com",
    "category":"TDM",
    "description": """
        Purchase Request & Report Purchase Requisition
    """,
    "depends":["purchase","purchase_requisition","product","hr","wtc_branch","wtc_approval","wtc_sequence","wtc_purchase_order"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
            "wtc_purchase_requisition_report.xml",
            "wtc_approval_pr_workflow.xml",
            "wtc_purchase_requisition_view.xml",
            "wtc_approval_pr_view.xml",
            "security/ir_rule.xml",
            "security/res_groups.xml",
            "data/wtc_approval_config_data.xml",
            ],
    "active":False,
    "installable":True
}
