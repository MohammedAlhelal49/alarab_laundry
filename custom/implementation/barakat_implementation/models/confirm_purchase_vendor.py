from odoo import models, fields, api

class ConfirmPurchaseWizard(models.TransientModel):
    _name = 'confirm.purchase.wizard'
    _description = 'Confirm Purchase Order Wizard'

    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        purchase = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        res['purchase_id'] = purchase.id
        res['vendor_id'] = purchase.partner_id.id
        return res

    def confirm_purchase_order(self):
        self.purchase_id.partner_id = self.vendor_id.id

        # Call confirm but skip wizard this time
        self.purchase_id.with_context(skip_vendor_wizard=True).button_confirm()
