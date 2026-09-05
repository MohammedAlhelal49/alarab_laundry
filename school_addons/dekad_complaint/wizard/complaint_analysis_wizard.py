import time
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DeComplaintAnalysisWizard(models.TransientModel):
    """ complaint Analysis Wizard """
    _name = "de.complaint.analysis.wizard"
    _description = "complaint Analysis Wizard"

    created_by = fields.Selection([
        ('student', 'Student'), ('teacher', 'Teacher'),
        ('parent', 'Parent'),
    ], 'Created By', required=True)

    def print_report(self):
        data = self.read(
            ['created_by'])[0]
        report = self.env.ref(
            'dekad_complaint.act_open_de_complaint_analysis_report_view'
        )
        return report.report_action(self, data=data)
