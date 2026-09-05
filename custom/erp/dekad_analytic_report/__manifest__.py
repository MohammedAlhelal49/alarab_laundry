
{
    'name': 'Analytical Item Report PDF',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'PDF Print with Group By for Analytical Item Report',
    'depends': ['base','analytic', 'account','spreadsheet_dashboard', 'purchase','sale'],
    'description': """    
        -- Add Payment Method to Analytic Items automatically based on invoice payments.
    
        -- Categorize payment methods into Cash, Visa/Card, Thiqa, and 3rd Party for reporting purposes.
    
        -- Add an Analytic Account field on customer invoices and automatically distribute it to invoice lines.
    
        -- Optionally apply the invoice Analytic Account to Receivable journal items through Journal configuration.
    
        -- Add Payment Method to Analytic Item form, list, search, and group by views.
    
        -- Add a Spreadsheet Dashboard for revenue analysis including Gross Revenue, Net Revenue, Monthly Revenue, Revenue by Payment Method, KPI cards, and Deductions analysis.
    
        -- Add an Analytical Report wizard to print grouped PDF reports with summary totals and optional detailed transaction lines.
        
        -- adds the Payment Method of the related Invoice to the Analytic Report.
        
        -- Prevent deletion of analytic accounts used by confirmed documents

    
    """,

    'data': [
        'data/dr_revenue_dashboard_data.xml',

        'security/ir.model.access.csv',
        'wizard/analytical_item_print_wizard.xml',
        'report/analytical_item_report_template.xml',
        'views/account_analytic_line_views.xml',
        'views/analytical_item_report_view.xml',
        'views/account_journal_view.xml',
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',

    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
