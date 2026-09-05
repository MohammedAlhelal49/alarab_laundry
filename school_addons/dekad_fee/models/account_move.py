from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    student_id = fields.Many2one('op.student', string='Student', copy=False)


    @api.onchange('student_id')
    def _onchange_student_id(self):
     for rec in self:
         if rec.student_id:
          # keep invoice partner synced with student partner
          rec.partner_id = rec.student_id.partner_id