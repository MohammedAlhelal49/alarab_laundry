###############################################################################

from odoo import models, fields, api


class DeTeacher(models.Model):
    _inherit = 'de.teacher'

    health_checkup_ids = fields.One2many(
        'de.health.checkup', 'teacher_id', 'Health checkup Detail')

    @api.model_create_multi
    def create(self, vals):
        res = super(DeTeacher, self).create(vals)
        self.env['de.health'].create({'teacher_id': res.id, 'type': 'teacher'})
        return res
