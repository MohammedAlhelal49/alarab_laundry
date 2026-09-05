from odoo import models, fields, api


class DeNote(models.Model):
    _name = "de.note"
    _description = "Note"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = " create_date DESC"
    _rec_name = "sequence"

    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.note'))
    name = fields.Char(string='Name', required=True)
    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name",copy=False)  # Added by Ahmed
    description = fields.Text('Description')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')],
                             string="State", default="draft", tracking=True, copy=False)

    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'High')], string='Priority')

    group_id = fields.Many2one('de.note.group', 'Group', required=True)


    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeNote, self).copy(default)

    def set_confirm(self):
        self.state = 'confirm'

    def set_draft(self):
        self.state = 'draft'
