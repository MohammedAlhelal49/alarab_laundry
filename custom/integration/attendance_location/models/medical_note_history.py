# attendance_location/models/medical_note_history.py
from odoo import models, fields, api

class MedicalNoteHistory(models.Model):
    _name = 'attendance_location.medical_note_history'
    _description = 'Patient Medical Note History'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    patient_id = fields.Many2one(
        'attendance_location.patient',
        string='Patient',
        required=True,
        ondelete='cascade'
    )
    title = fields.Char(string='Title', required=True)
    note_text = fields.Text(string='Description')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Filename')

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._post_message('created')
        return record

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._post_message('updated')
        return res

    def unlink(self):
        for rec in self:
            rec._post_message('deleted')
        return super().unlink()

    def _post_message(self, action_type):
        """Post update info to the patient's chatter."""
        for rec in self:
            message = (
                f"Medical Details:\n"
                f"Title: {rec.title or 'N/A'}\n"
                f"Description: {rec.note_text or 'N/A'}\n"
                f"Attachment: {rec.attachment_filename or 'None'}"
            )
            rec.patient_id.message_post(
                body=message,
                subject=f"Medical Note {action_type.title()}",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )