# dekad_real_estate/hooks.py

def assign_real_estate_groups(env):
    """
    Assign real estate permission groups to internal users on install.
    """
    internal_users = env.ref('base.group_user').users

    group_xml_ids = [
        'dekad_real_estate.group_enable_sale_properties',
        'dekad_real_estate.group_enable_rental_properties',
    ]

    for xml_id in group_xml_ids:
        group = env.ref(xml_id, raise_if_not_found=False)
        if group:
            group.users = [(4, user.id) for user in internal_users]

    # Recompute payment methods

    orders = env['sale.order'].search([])

    # Efficient batch compute
    orders._compute_payment_method_ids()