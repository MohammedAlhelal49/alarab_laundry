{
    'name': 'Dekad Pos Van Sales',
    'version': '1.0',
    'summary': 'Dekad pos van sales ',
    'description': '''
- Adds Is Van Sales" setting to POS configurations and allows linking a fleet vehicle to the POS.
- Restricts vehicle selection to those marked as Van Sale only.
- Automatically links the selected van to POS orders and displays the van name in POS Order views.
- Introduces "Van Assignment" management to link vans with drivers and customers.
- Supports dynamic customer filtering: drivers only see their assigned customers in POS.
- Adds a My Customers menu under POS for quick access and provides a kanban view of customers assigned to the current van driver.
''',
    'category': 'Fleet',
    'depends': ['base','point_of_sale','fleet' , 'dekad_additional_features'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_inherit.xml',
        'views/my_customer_view.xml',
        'views/fleet_vehicle_view.xml',
        'views/van_assignment_views.xml',
        'views/menu.xml',
    ],

    'installable': True,
    'application': True,
}
