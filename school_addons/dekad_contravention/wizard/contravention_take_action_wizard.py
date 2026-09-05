from odoo import fields, models, api


class DeContraventionTakeActionWizard(models.TransientModel):
    _name = "de.contravention.take.action.wizard"
    _description = "Contravention take action wizard"

    def default_get(self, fields):
        res = super(DeContraventionTakeActionWizard, self).default_get(fields)
        res['contravention_id'] = self.env.context.get('active_id')
        return res

    contravention_id = fields.Many2one('de.contravention', 'Contravention')

    start_date = fields.Date('Suspended From Date', default=fields.Date.today())
    end_date = fields.Date('Suspended To Date')
    is_suspend = fields.Boolean('Is suspended ?')
    is_penalty = fields.Boolean('Is penalty ?')
    penalty = fields.Integer('penalty Amount')
    is_alert = fields.Boolean('Send alert')
    alert = fields.Char('Alert')

    @api.constrains('start_date', 'end_date')
    def _check_date(self):
        if self.start_date and self.start_date < fields.date.today():
            raise models.ValidationError(
                'Student suspend start date cant be less than today')
        if self.start_date and self.end_date and (self.end_date < self.start_date):
            raise models.ValidationError(
                'Student suspend end date cant be less than start date')

    def take_action(self):
        suspend_env = self.env['de.student.suspend']
        penalty_env = self.env['de.student.penalty']
        for record in self:
            if record.is_suspend:
                suspend_env.create({
                    'student_id': record.contravention_id.student_id.id,
                    'start_date': record.start_date,
                    'end_date': record.end_date,
                    'contravention_id': record.contravention_id.id,
                })
            if record.is_penalty:
                penalty_env.create({
                    'contravention_id': record.contravention_id.id,
                    'student_id': record.contravention_id.student_id.id,
                    'penalty': record.penalty,
                })
            if record.is_alert:
                record.contravention_id.is_alert = True
                record.contravention_id.alert = record.alert

            record.contravention_id.state = 'action'
