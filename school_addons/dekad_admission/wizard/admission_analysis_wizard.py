import time
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DeAdmissionAnalysisWizard(models.TransientModel):
    _name = "de.admission.analysis.wizard"
    _description = "Admission Analysis Wizard"

    grade_id = fields.Many2one('de.grade', 'Grade', required=True)
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Date('End Date', required=True)

    def print_report(self):
        stat_date = fields.Date.from_string(self.start_date)
        end_date = fields.Date.from_string(self.end_date)
        if stat_date > end_date:
            raise ValidationError(
                _("End date can not be set before start date.")
            )
        else:
            data = self.read(
                ['grade_id', 'start_date', 'end_date'])[0]
            report = self.env.ref(
                'dekad_admission.act_open_de_admission_analysis_report_view'
            )
            return report.report_action(self, data=data)
