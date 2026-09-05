from odoo import fields, models, api


class DeContraventionChangePenaltyWizard(models.TransientModel):
    _name = "de.contravention.change.penalty.wizard"
    _description = "Contravention change penalty wizard"

    def default_get(self, fields):
        res = super(DeContraventionChangePenaltyWizard, self).default_get(fields)
        contravention = self.env['de.contravention'].browse(self.env.context.get('active_id'))
        res['contravention_id'] = self.env.context.get('active_id')
        is_suspend = len(contravention.suspend_ids)
        res['is_suspend'] = len(contravention.suspend_ids)
        res['start_date'] = contravention.suspend_ids[0].start_date if is_suspend else False
        res['end_date'] = contravention.suspend_ids[0].end_date if is_suspend else False
        is_penalty = len(contravention.penalty_ids)
        res['is_penalty'] = len(contravention.penalty_ids)
        res['penalty'] = contravention.penalty_ids[0].penalty if is_penalty else False
        res['is_alert'] = contravention.is_alert
        res['alert'] = contravention.alert
        return res

    contravention_id = fields.Many2one('de.contravention', 'Contravention')
    start_date = fields.Date('Suspended From Date')
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
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise models.ValidationError(
                'Student suspend end date cant be less than start date')

    def change_penalty(self):
        for record in self:
            if record.is_suspend:
                record.contravention_id.suspend_ids[0].write({'start_date': record.start_date,
                                                              'end_date': record.end_date, }
                                                             )
            if record.is_penalty:
                record.contravention_id.penalty_ids[0].write({'penalty': record.penalty,
                                                              }
                                                             )

            if record.is_alert:
                record.contravention_id.alert = record.alert
