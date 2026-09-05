from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_inv_receipt = fields.Boolean(string="Enable Automatic Inventory Receipt", default=False)
    auto_inv_delivery = fields.Boolean(string="Enable Automatic Inventory Delivery", default=False)
    require_picking_signature = fields.Boolean(
        string='Require Signature Before Transfer Validation',
        default=False,
        help='Require a recipient signature before validating outgoing and internal transfers.'
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # We link these to the company_id so they change when you switch companies
    auto_inv_receipt = fields.Boolean(
        related='company_id.auto_inv_receipt',
        readonly=False,
        string="Automatic Inventory Receipt"
    )
    auto_inv_delivery = fields.Boolean(
        related='company_id.auto_inv_delivery',
        readonly=False,
        string="Automatic Inventory Delivery"
    )

    require_picking_signature = fields.Boolean(
        related='company_id.require_picking_signature',
        readonly=False,
    )