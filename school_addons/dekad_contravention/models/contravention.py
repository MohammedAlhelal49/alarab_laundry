from odoo import models, fields, api


class DeContravention(models.Model):
    _name = "de.contravention"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Contraventions"
    _rec_name = "sequence"

    grade_id = fields.Many2one('de.grade', 'Grade', tracking=True)

    student_id = fields.Many2one('de.student', 'Student', tracking=True, ondelete="cascade")

    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].sudo().next_by_code('de.contravention'))

    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'High')], string='Priority')

    category_id = fields.Many2one('de.contravention.category', 'Category', tracking=True,
                                  required=True)
    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name", copy=False)  # Added by Ahmed
    penalty_ids = fields.One2many(
        'de.student.penalty', 'contravention_id', 'Penalty')

    suspend_ids = fields.One2many(
        'de.student.suspend', 'contravention_id', 'Suspend')

    details = fields.Text('Details')

    is_alert = fields.Boolean('Send alert')
    alert = fields.Char('Alert')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'confirmed'),
         ('action', 'Action Taken')],
        string="State", default="draft", tracking=True)

    @api.onchange('grade_id')
    def _onchange_grade_id(self):
        for rec in self:
            if rec.grade_id != rec.student_id.grade:
                rec.student_id = False

    def set_confirm(self):
        self.state = 'confirm'

    def set_draft(self):
        self.state = 'draft'

    def set_action(self):
        self.state = 'action'

    def set_cancel(self):
        self.state = 'confirm'
        self.suspend_ids.unlink()
        self.penalty_ids.unlink()
        self.is_alert = False
        self.alert = False

# ADDED: Override name_get to handle the AttributeError
    def name_get(self):
        result = []
        for record in self:
            # Use sequence if available, otherwise use category + student, otherwise use ID
            if record.sequence:
                name = record.sequence
            elif record.category_id and record.student_id:
                name = f"{record.category_id.name} - {record.student_id.name}"
            elif record.category_id:
                name = record.category_id.name
            else:
                name = f'Contravention #{record.id}' if record.id else 'New Contravention'
            result.append((record.id, name))
        return result




















