from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_sale_properties = fields.Boolean(
        string="Enable Sale Properties",
        default=True,
        help="Enable features related to property sales, including access to Sales Contracts."
    )

    enable_rental_properties = fields.Boolean(
        string="Enable Rental Properties",
        default=True,
        help="Enable features related to property rentals, including access to Rental Contracts and Calendar."
    )

    enforce_product_price_limits = fields.Boolean(
        string="Enforce Product Price Limits",
        help="When enabled, the system will block sale order line prices outside the min/max defined on the product."
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_sale_properties = fields.Boolean(
        string="Enable Sale Properties",
        related='company_id.enable_sale_properties',
        readonly=False
    )

    enable_rental_properties = fields.Boolean(
        string="Enable Rental Properties",
        related='company_id.enable_rental_properties',
        readonly=False
    )

    def set_values(self):
        res = super().set_values()
        self._update_sale_property_group()
        self._update_rental_property_group()
        return res

    def _update_sale_property_group(self):
        group = self.env.ref('dekad_real_estate.group_enable_sale_properties', raise_if_not_found=False)
        if not group:
            return

        target_company_users = self.company_id.user_ids
        all_users = self.env['res.users'].search([])

        for user in all_users:
            if user in target_company_users:
                if self.enable_sale_properties and group not in user.groups_id:
                    user.groups_id += group
                elif not self.enable_sale_properties and group in user.groups_id:
                    user.groups_id -= group
            else:
                # remove from other company users just in case
                if group in user.groups_id:
                    user.groups_id -= group

    def _update_rental_property_group(self):
        group = self.env.ref('dekad_real_estate.group_enable_rental_properties', raise_if_not_found=False)
        if not group:
            return

        target_company_users = self.company_id.user_ids
        all_users = self.env['res.users'].search([])

        for user in all_users:
            if user in target_company_users:
                if self.enable_rental_properties and group not in user.groups_id:
                    user.groups_id += group
                elif not self.enable_rental_properties and group in user.groups_id:
                    user.groups_id -= group
            else:
                if group in user.groups_id:
                    user.groups_id -= group


    enforce_product_price_limits = fields.Boolean(
        string="Enforce Product Price Limits",
        related='company_id.enforce_product_price_limits',
        readonly=False
    )