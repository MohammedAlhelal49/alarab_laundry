def assign_sale_order_groups(env):
    """
    Assign all custom permission groups
    to internal users during module install.
    """

    internal_group = env.ref('base.group_user')
    users = internal_group.users

    # All custom permission groups to enable by default
    group_xml_ids = [
        # ✅ Sales
        'dekad_erp_additional_permissions.group_sale_order_confirm',
        'dekad_erp_additional_permissions.group_sale_order_cancel',
        'dekad_erp_additional_permissions.group_sale_order_deletion',

        # ✅ Purchase
        'dekad_erp_additional_permissions.group_purchase_order_confirm',
        'dekad_erp_additional_permissions.group_purchase_order_cancel',
        'dekad_erp_additional_permissions.group_purchase_order_delete',

        # ✅ Inventory
        'dekad_erp_additional_permissions.group_stock_picking_delete',
        'dekad_erp_additional_permissions.group_stock_picking_cancel',
        'dekad_erp_additional_permissions.group_stock_picking_validate',
        'dekad_erp_additional_permissions.group_stock_picking_return',

        # ✅ Accounting
        'dekad_erp_additional_permissions.group_account_move_post',
        'dekad_erp_additional_permissions.group_account_move_cancel',
        'dekad_erp_additional_permissions.group_account_move_delete',
        'dekad_erp_additional_permissions.group_account_move_reset_to_draft',

        'dekad_erp_additional_permissions.group_account_account_delete',
        'dekad_erp_additional_permissions.group_account_account_create',

        'dekad_erp_additional_permissions.group_account_payment_confirm',
        'dekad_erp_additional_permissions.group_account_payment_cancel',
        'dekad_erp_additional_permissions.group_account_payment_delete',
        'dekad_erp_additional_permissions.group_account_payment_draft',

        # ✅ products
        'dekad_erp_additional_permissions.group_product_product_delete',
        'dekad_erp_additional_permissions.group_product_product_create',
        # ✅ contact
        'dekad_erp_additional_permissions.group_contact_create',
        'dekad_erp_additional_permissions.group_contact_delete',
    ]

    for xml_id in group_xml_ids:
        group = env.ref(xml_id, raise_if_not_found=False)
        if group:
            group.users = [(4, user.id) for user in users]
