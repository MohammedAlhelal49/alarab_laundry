
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from odoo.tools import html2plaintext


class ResPartner(models.Model):
    _inherit = 'res.partner'

    nationality = fields.Many2one('res.country', string='Nationality')
    id_number = fields.Char(string='ID No.')
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'res.partner')],
        string='Attachments'
    )








