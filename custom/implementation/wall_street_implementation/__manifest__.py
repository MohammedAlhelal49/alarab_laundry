{
    'name': 'Wall Street Implementation',
    'version': '18.0.1.0.0',
    'summary': 'Custom Quotation & Invoice report design',
    'category': 'Accounting',
    'depends': ['sale', 'account'],
    'data': [
        'report/report_shared_body.xml',
        'report/report_saleorder.xml',
        #'report/report_invoice.xml',
        'report/report_layout.xml',
        'views/sale_order_view.xml',
        'views/report_action.xml',
        'views/product_category_view.xml',
    ],
    'installable': True,
    'post_init_hook': '_set_report_layout',
}