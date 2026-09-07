from odoo import api, models, Command


DEFAULT_PERMISSION_GROUP_XMLIDS = [
    # Sales
    'dekad_erp_additional_permissions.group_sale_order_confirm',
    'dekad_erp_additional_permissions.group_sale_order_cancel',
    'dekad_erp_additional_permissions.group_sale_order_deletion',

    # Purchase
    'dekad_erp_additional_permissions.group_purchase_order_confirm',
    'dekad_erp_additional_permissions.group_purchase_order_cancel',
    'dekad_erp_additional_permissions.group_purchase_order_delete',

    # Inventory
    'dekad_erp_additional_permissions.group_stock_picking_delete',
    'dekad_erp_additional_permissions.group_stock_picking_cancel',
    'dekad_erp_additional_permissions.group_stock_picking_validate',
    'dekad_erp_additional_permissions.group_stock_picking_return',

    # Accounting
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

    # Products
    'dekad_erp_additional_permissions.group_product_product_delete',
    'dekad_erp_additional_permissions.group_product_product_create',

    # Contacts
    'dekad_erp_additional_permissions.group_contact_update',
    'dekad_erp_additional_permissions.group_contact_create',
    'dekad_erp_additional_permissions.group_contact_delete',
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_default_permission_groups(self):
        groups = self.env['res.groups']

        for xml_id in DEFAULT_PERMISSION_GROUP_XMLIDS:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group:
                groups |= group

        return groups

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)

        internal_group = self.env.ref('base.group_user')
        default_groups = self._get_default_permission_groups()

        for user in users:
            if internal_group in user.groups_id:
                user.write({
                    'groups_id': [
                        Command.link(group.id)
                        for group in default_groups
                    ]
                })

        return users