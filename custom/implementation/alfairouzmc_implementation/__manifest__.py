{
    'name': 'Al Fairouz MC Implementation',
    'version': '18.0.1.0.0',
    'summary': 'Customer-specific implementation and customizations for Al Fairouz MC',
    'description': """
        This module contains all custom developments specific to Al Fairouz MC.
    """,
    'category': 'Customization',
    'depends': [
        'stock',
        'analytic',
    ],
    'data': [
        'report/move_analyze_report.xml',
        'report/move_analyze_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
#A "Move Analysis" print report feature that allows the user to
# select multiple move records within the Move Analysis screen
# and print them into a single PDF, grouped by analytical account.
#Negative stock restriction , A new setting named "Restrict negative stock output" has been added to the settings page.
# When enabled, a field appears allowing you to select a specific list of users
# who are permitted to issue negative stock quantities.
