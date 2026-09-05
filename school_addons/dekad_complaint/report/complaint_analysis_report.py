import time

from odoo import models, api


class DeComplaintAnalysisReport(models.AbstractModel):
    _name = "report.dekad_complaint.de_complaint_analysis_report"
    _description = "complaint Analysis Report"

    def get_data(self, data):
        created_by = data['created_by']
        complaints = self.env['de.complaint'].search([('created_by', '=', created_by)])
        return complaints

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'data': data,
            'created_by': data['created_by'],
            'complaints': self.get_data(data),
        }
        return docargs














