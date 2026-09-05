from odoo import models, fields, api, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # Contact fields
    dekad_contact_name = fields.Char(string='Contact Name')
    dekad_company_name = fields.Char(string='Company Name')
    dekad_email = fields.Char(string='Email')
    dekad_phone = fields.Char(string='Phone')

    # Custom request fields
    dekad_request_type = fields.Char(string='Request Type')
    dekad_industry = fields.Char(string='Company Field / Industry')
    dekad_employees = fields.Integer(string='Number of Employees')
    dekad_demo_date = fields.Datetime(string='Preferred Date & Time')

    # Link to the generated lead
    dekad_lead_id = fields.Many2one('crm.lead', string='Generated Lead', readonly=True, copy=False)

    def action_convert_ticket_to_lead_or_opportunity(self):
        """Creates a CRM Lead from the Ticket data."""
        self.ensure_one()

        if self.dekad_lead_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.dekad_lead_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        lead_vals = {
            'name': self.name,
            'contact_name': self.dekad_contact_name,
            'partner_name': self.dekad_company_name,
            'email_from': self.dekad_email,
            'phone': self.dekad_phone,
            'type': 'lead',
            'description': self.description,
            'dekad_request_type': self.dekad_request_type,
            'dekad_industry': self.dekad_industry,
            'dekad_employees': self.dekad_employees,
            'dekad_demo_date': self.dekad_demo_date,
        }

        new_lead = self.env['crm.lead'].sudo().create(lead_vals)
        self.dekad_lead_id = new_lead.id

        self.message_post(
            body=f"Converted to Lead: <a href='#' data-oe-model='crm.lead' data-oe-id='{new_lead.id}'>{new_lead.name}</a>")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': new_lead.id,
            'view_mode': 'form',
            'target': 'current',
        }
