from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    gmr_request_ids = fields.Many2many(
        'gmr.request',
        'gmr_request_account_move_rel',
        'move_id',
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

    def action_post(self):
        res = super().action_post()
        for move in self:
            # 'bill_created' -> first-time posting.
            # 'approved' -> the bill was previously cancelled (which reverts
            # the request to 'approved'), then reused/reposted instead of
            # creating a brand new bill via the wizard.
            requests = move.gmr_request_ids.filtered(
                lambda r: r.state in ('bill_created', 'approved')
            )
            for request in requests:
                # A request can have several bills (one per vendor, from a
                # multi-vendor split). Only mark it 'done' once every
                # non-cancelled bill on it is actually posted -- otherwise
                # a single posted bill would mark the whole request done
                # while another vendor's bill is still in draft.
                still_pending = request.account_move_ids.filtered(
                    lambda m: m.state not in ('posted', 'cancel')
                )
                new_state = 'done' if not still_pending else 'bill_created'
                if request.state != new_state:
                    request.with_context(
                        mail_notrack=True,
                        tracking_disable=True,
                    ).write({'state': new_state})
        return res

    def button_cancel(self):
        res = super().button_cancel()
        for move in self:
            requests = move.gmr_request_ids.filtered(
                lambda r: r.state in ('bill_created', 'done')
            )
            for request in requests:
                other_active_bills = request.account_move_ids.filtered(
                    lambda m: m.state != 'cancel'
                )
                if other_active_bills:
                    continue
                request.with_context(
                    mail_notrack=True,
                    tracking_disable=True,
                ).write({'state': 'approved'})
                request.message_post(body=_(
                    'Vendor Bill %s was cancelled. This request has been '
                    're-opened at "Approved" so a new PO/Bill can be created.'
                ) % move.name)
        return res