import time

from odoo import models, api


class DeAdmissionAnalysisReport(models.AbstractModel):
    _name = "report.dekad_admission.de_admission_analysis_report"
    _description = "Admission Analysis Report"

    def get_total_student(self, data):
        student_search = self.env['de.admission'].search_count(
            [('state', '=', 'confirm'),
             ('grade_id', '=', data['grade_id'][0]),
             ('admission_date', '>=', data['start_date']),
             ('admission_date', '<=', data['end_date'])])
        return student_search

    def get_data(self, data):
        lst = []
        student_search = self.env['de.admission'].search(
            [('state', '=', 'confirm'),
             ('grade_id', '=', data['grade_id'][0]),
             ('admission_date', '>=', data['start_date']),
             ('admission_date', '<=', data['end_date'])],
            order='admission_date desc')
        res = {}
        total_student = 0
        for student in student_search:
            total_student += 1
            res = {
                'name': student.student_id.name,
                'sequence': student.sequence,
                'admission_date': student.admission_date,
            }
            lst.append(res)
        return lst

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
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'get_total_student': self.get_total_student(data),
            'get_data': self.get_data(data)
        }
        return docargs
