# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError
from odoo.exceptions import UserError


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    show_product_variation_attribute_name = fields.Boolean()
    attachment_ids = fields.One2many(
        "company.attachment",
        "company_id",
        string="Company Attachments",
    )
    show_report_signature = fields.Boolean(
        string="Show Signature Section",
        default=False,
    )

    attachment_count = fields.Integer(
        compute="_compute_attachment_count",
        string="Attachments",
    )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for company in self:
            company.attachment_count = len(company.attachment_ids)

    def action_view_company_attachments(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Company Attachments",
            "res_model": "company.attachment",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.id)],
            "context": {
                "default_company_id": self.id,
            },
        }


class ResConfigSettingsInherited(models.TransientModel):
    _inherit = 'res.config.settings'

    show_product_variation_attribute_name = fields.Boolean(related="company_id.show_product_variation_attribute_name",
                                                           readonly=False)
    prevent_multi_company_mod = fields.Boolean(
        string="Prevent Multi-Company Updates",
        config_parameter="multi_company_lock.prevent_edit",
        help="If enabled, users cannot edit records while multiple companies are active."
    )



class ApplyModulesWizard(models.TransientModel):
    _name = 'apply.modules.wizard'
    _description = 'Install / Upgrade / Uninstall / Remove Modules Wizard'

    modules_to_install = fields.Text(
        string="Modules to Install",
        help="Comma-separated module technical names"
    )

    modules_to_upgrade = fields.Text(
        string="Modules to Upgrade",
        help="Comma-separated module technical names (must be installed)"
    )

    modules_to_uninstall = fields.Text(
        string="Modules to Uninstall",
        help="Comma-separated module technical names"
    )

    modules_to_remove_from_apps = fields.Text(
        string="Modules to Remove from Apps List",
        help="Comma-separated module technical names"
    )

    # --------------------------------------------------
    # MAIN BUTTON
    # --------------------------------------------------
    def action_apply(self):
        self.ensure_one()

        self._install_modules()
        self._upgrade_modules()
        self._uninstall_modules()
        self._remove_modules_from_apps()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Done'),
                'message': _('Modules have been processed successfully.'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    # --------------------------------------------------
    # INSTALL
    # --------------------------------------------------
    def _install_modules(self):
        if not self.modules_to_install:
            return

        module_names = self._parse_modules(self.modules_to_install)

        modules = self.env['ir.module.module'].search([
            ('name', 'in', module_names),
            ('state', 'in', ['uninstalled', 'to install', 'to upgrade']),
        ])

        for module in modules:
            module.button_immediate_install()

    # --------------------------------------------------
    # UPGRADE
    # --------------------------------------------------
    def _upgrade_modules(self):
        if not self.modules_to_upgrade:
            return

        module_names = self._parse_modules(self.modules_to_upgrade)

        modules = self.env['ir.module.module'].search([
            ('name', 'in', module_names),
            ('state', '=', 'installed'),
        ])

        for module in modules:
            module.button_immediate_upgrade()

    # --------------------------------------------------
    # UNINSTALL
    # --------------------------------------------------
    def _uninstall_modules(self):
        if not self.modules_to_uninstall:
            return

        module_names = self._parse_modules(self.modules_to_uninstall)

        modules = self.env['ir.module.module'].search([
            ('name', 'in', module_names),
            ('state', '=', 'installed'),
        ])

        for module in modules:
            module.button_immediate_uninstall()

    # --------------------------------------------------
    # REMOVE FROM APPS LIST (HARD DELETE)
    # --------------------------------------------------
    def _remove_modules_from_apps(self):
        if not self.modules_to_remove_from_apps:
            return

        module_names = self._parse_modules(self.modules_to_remove_from_apps)

        modules = self.env['ir.module.module'].search([
            ('name', 'in', module_names),
        ])

        modules.unlink()

    # --------------------------------------------------
    # UTIL
    # --------------------------------------------------
    def _parse_modules(self, text):
        return [name.strip() for name in text.split(',') if name.strip()]





