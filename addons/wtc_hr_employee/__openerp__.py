{
    "name":"Employee",
    "version":"1.0",
    "author":"PT. WITACO",
    "website":"http://witaco.com",
    "category":"TDM",
    "description": """
        Addons Employee
    """,
    "depends":["base","hr","wtc_address","wtc_branch","hr_attendance","teds_api_configuration"],
    "init_xml":[],
    "demo_xml":[],
    "data":["data/res_groups.xml",
            "wtc_hr_employee_view.xml",
            "wtc_hr_job_view.xml",
            "wtc_hr_department.xml",
            "wtc_branch_view.xml",
            "security/res_groups.xml",
            "security/res_groups_button.xml",
            ],
    "active":False,
    "installable":True
}
