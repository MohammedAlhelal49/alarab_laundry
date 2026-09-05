from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64


class ResPartner(models.Model):
    _inherit = "res.partner"
    attachment_ids = fields.One2many('de.attachment', 'partner_id', string="Attachments")


class DeAttachment(models.Model):
    _name = 'de.attachment'
    _description = "attachment"
    partner_id = fields.Many2one('res.partner', string="Partner", ondelete="cascade")
    name = fields.Char(string="Name", required=True)
    file = fields.Binary(string="File", required=True)

    @api.onchange('file')
    @api.constrains('file')
    def _check_file_size(self):
        max_file_size = 5 * 1024 * 1024  # 5 MB in bytes
        for attachment in self:
            if attachment.file:
                file_data = base64.b64decode(attachment.file)
                file_size = len(file_data)
                if file_size > max_file_size:
                    raise ValidationError(f"File size for the attachment ({attachment.name}) cannot exceed 5 MB!")
