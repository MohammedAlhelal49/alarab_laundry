from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    nb_attachment = fields.Integer(
        compute="_compute_nb_attachment",
        store=False
    )

    def _compute_nb_attachment(self):
        for record in self:
            record.nb_attachment = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', record.id)
            ])

    def attach_document(self, **kwargs):
        attachment_ids = kwargs.get('attachment_ids', [])
        attachments = self.env['ir.attachment'].browse(attachment_ids)

        attachments.write({
            'res_model': 'purchase.order',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }