from odoo import models, fields, api



class PosReceipt(models.Model):
    """
        This is an Odoo model for Point of Sale (POS).
        It creates a new model of pos.receipt for providing different types of
        receipt design.
    """
    _name = 'pos.receipt'
    _description = 'POS Receipts'

    name = fields.Char(string='Name', help='Name of the pos receipt')
    design_receipt = fields.Text(string='Receipt XML',
                                 help='Add your customised receipts for pos')

class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_send_whatsapp(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "res_model": "send.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_pos_order_id": self.id,
                "default_template_id": self.env.ref(
                    "alarab_laundry_implementation.whatsapp_pos_ready_template"
                ).id,
            },
        }


    def _export_for_ui_with_invoice(self):
        """ export order with invoice number"""
        data = super(PosOrder, self)._export_for_ui() if hasattr(super(), "_export_for_ui") else {}
        # fallback if no super
        data.update({
            'id': self.id,
            'pos_reference': self.pos_reference,
            'amount_total': self.amount_total,
            'invoice_number': self.account_move.sudo().name if self.account_move else False,
        })
        return data

    @api.model
    def sync_from_ui(self, orders):
        """Override sync_from_ui to inject invoice_number in response"""
        res = super().sync_from_ui(orders)
        if "pos.order" in res:
            for order in res["pos.order"]:
                pos = self.browse(order["id"])
                order["invoice_number"] = pos.account_move.sudo().name if pos.account_move else False
        return res
