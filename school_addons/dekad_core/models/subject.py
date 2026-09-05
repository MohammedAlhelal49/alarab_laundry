from odoo import models, fields


class DeSubject(models.Model):
    _name = 'de.subject'
    _description = 'Subject'

    name = fields.Char(string='Subject Name', required=True)
    teacher_ids = fields.Many2many('de.teacher', string='teacher(s)')
    grade_id = fields.Many2one('de.grade', string='Grade', ondelete='cascade')
    _sql_constraints = [('unique_name', 'unique(grade_id,name)', 'Subject Name must be unique per grade!')]
