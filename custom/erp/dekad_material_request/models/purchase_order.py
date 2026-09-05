from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    gmr_request_ids = fields.Many2many(
        'gmr.request',
        'gmr_request_purchase_order_rel',
        'order_id',
        'request_id',
        string='Material Requests',
        readonly=True
    )

    gmr_request_count = fields.Integer(
        string='Material Requests',
        compute='_compute_gmr_request_count'
    )

    @api.depends('gmr_request_ids')
    def _compute_gmr_request_count(self):
        for rec in self:
            rec.gmr_request_count = len(rec.gmr_request_ids)

    def action_view_gmr_requests(self):
        self.ensure_one()
        if len(self.gmr_request_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'gmr.request',
                'res_id': self.gmr_request_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requests'),
            'res_model': 'gmr.request',
            'domain': [('id', 'in', self.gmr_request_ids.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            # 'po_created' -> first-time confirmation.
            # 'approved' -> the PO was previously cancelled (which reverts the
            # request to 'approved'), then reset to draft and reused/reconfirmed
            # instead of creating a brand new PO via the wizard.
            requests = order.gmr_request_ids.filtered(
                lambda r: r.state in ('po_created', 'approved')
            )
            for request in requests:
                # A request can have several POs (one per vendor, from a
                # multi-vendor split). Only mark it 'done' once every
                # non-cancelled PO on it is actually confirmed -- otherwise
                # a single confirmed PO would mark the whole request done
                # while another vendor's PO is still sitting in draft.
                still_pending = request.purchase_order_ids.filtered(
                    lambda o: o.state not in ('purchase', 'done', 'cancel')
                )
                new_state = 'done' if not still_pending else 'po_created'
                if request.state != new_state:
                    request.with_context(
                        mail_notrack=True,
                        tracking_disable=True,
                    ).write({'state': new_state})
        return res

    def button_cancel(self):
        res = super().button_cancel()
        for order in self:
            requests = order.gmr_request_ids.filtered(
                lambda r: r.state in ('po_created', 'done')
            )
            for request in requests:
                other_active_pos = request.purchase_order_ids.filtered(
                    lambda o: o.state != 'cancel'
                )
                if other_active_pos:
                    continue
                request.with_context(
                    mail_notrack=True,
                    tracking_disable=True,
                ).write({'state': 'approved'})
                request.message_post(body=_(
                    'Purchase Order %s was cancelled. This request has been '
                    're-opened at "Approved" so a new PO/Bill can be created.'
                ) % order.name)
        return res