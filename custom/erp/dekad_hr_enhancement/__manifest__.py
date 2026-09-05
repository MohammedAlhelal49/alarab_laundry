{
    'name': 'HR Enhancement',
    'version': '18.0.1.0.1',
    'summary': 'HR Employee and Contract Enhancements',
    'description': """
        Extends HR Employee and Contract models with:
        -- Add a dedicated My Profile menu allowing employees to view their own profile.
        
        -- Add PRO, Labor Card Number, Employment Status, Employment Type, Last Working Date and Cancellation Date to Employee records.
        
        -- Organize employee Identification, Passport, Visa, Insurance and Work Permit information into a dedicated Documents tab with attachment support.
        
        -- Automatically create Activities and send Email reminders before the expiry of Employee Documents including ID, Passport, Visa, Work Permit and Insurance.
        
        -- Configure reminder intervals and the Email Template from HR Settings.
        
        -- Add Actual Start Date and Total UAE Allowances to Employee Contracts.
        
        -- Add a separate Visa Contract tab with additional Job Position, Wage, Schedule Pay and Allowance information.
        
        -- Add a customized List View for the Time Off Analysis report.

    """,
    'category': 'Human Resources',
    'depends': [
        'hr',
        'hr_contract',
        'l10n_ae_hr_payroll',
        'hr_employee_updation',
        'mail',"hr_holidays"
    ],
    'data': [
        'data/activity_type.xml',
        'data/mail_template.xml',
        'data/ir_cron.xml',
        'views/profile_view.xml',
        'views/res_config_settings_view.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_report_views.xml',

    ],
    'installable': True,
    'application': False,
}