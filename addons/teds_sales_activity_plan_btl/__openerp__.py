{
    'name': 'TEDS Sales Activity PLAN & BTL',
    'version': '1.0',
    'description': 'TEDS Sales Activity PLAN & BTL',
    'summary': 'Sales Activity Plan',
    'sequence': '1', 
    'category': 'TDM',
    'author': 'TDM',
    'depends': ['base','teds_sales_activity_plan','dealer_sale_order','teds_api_configuration'],
    'demo': [],
    'data': [
        
        'views/teds_act_type_view.xml',
        'views/teds_sales_plan_activity_view.xml',
        'views/teds_sales_plan_activity_approve_view.xml',
        'views/teds_sales_plan_activity_review_view.xml',
        'views/teds_sale_plan_activity_approve_operation.xml',
        'views/teds_sales_result_activity_view.xml',
        'views/teds_sales_plan_activity_add_view.xml',
        'views/teds_sales_plan_activity_reject_view.xml',
        # 'views/teds_activity_btl_biaya_view.xml',
        
        'views/dealer_sale_order_view.xml',
        'views/dealer_spk_view.xml',
        'views/teds_b2b_api_sales_plan_view.xml',
        
        'report/teds_sale_activity_report_view.xml',
        'report/teds_sales_activity_print_view.xml',
        'report/teds_sales_activity_ansuransi_report_view.xml',

        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'security/res_groups_button.xml',
        'security/ir_rule.xml',

        'data/teds_act_type.xml',
        'data/teds_sales_plan_scheduled_actions.xml',
    ],
    'active': False,
    'application' : True,
    'installable': True
}