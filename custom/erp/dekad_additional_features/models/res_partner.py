import re
import urllib.parse
import phonenumbers
from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    related_user_id = fields.Many2one(
        'res.users',
        string='Related User'
    )


    country_id = fields.Many2one(
        'res.country', string='Country', required=True, default=lambda self: self.env.ref('base.ae').id
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def handle_current_users_contacts(self):
        for rec in self.env['res.users'].search([]):
            rec.partner_id.related_user_id = rec.id

    def action_send_whatsapp(self):
        """Wizard-like selection of template"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "send.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id,
                        "default_template_id": self.env.ref("dekad_additional_features.whatsapp_default_template").id,
                        },
        }


class ResUserInherited(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals):
        res = super(ResUserInherited, self).create(vals)
        for rec in res:
            rec.partner_id.related_user_id = rec.id
        return res
