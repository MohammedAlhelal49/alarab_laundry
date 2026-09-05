from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Contact fields to hold data before CRM conversion
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

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Ensure tasks aren't "Private" if they come from your website
        # You should replace 'YOUR_PROJECT_ID' with the actual ID of your 'Inquiries' project
        for vals in vals_list:
            if not vals.get('project_id') and vals.get('dekad_request_type'):
                # Force assign to a project to avoid "Private" status
                # You can find the ID in Project > Configuration > Projects
                vals['project_id'] = self.env['project.project'].search([('name', '=', 'Website Inquiries')],
                                                                        limit=1).id

        # 2. Create the task records
        tasks = super(ProjectTask, self).create(vals_list)

        # 3. Handle Helpdesk Ticket creation
        for task in tasks:
            if task.dekad_request_type:
                # Map ALL fields from Task to Ticket
                self.env['helpdesk.ticket'].sudo().create({
                    'name': f"{task.dekad_request_type}: {task.dekad_contact_name or task.name}",
                    'description': task.description,
                    'dekad_contact_name': task.dekad_contact_name,
                    'dekad_company_name': task.dekad_company_name,
                    'dekad_email': task.dekad_email,
                    'dekad_phone': task.dekad_phone,
                    'dekad_request_type': task.dekad_request_type,
                    'dekad_industry': task.dekad_industry,
                    'dekad_employees': task.dekad_employees,
                    'dekad_demo_date': task.dekad_demo_date,
                })

        return tasks