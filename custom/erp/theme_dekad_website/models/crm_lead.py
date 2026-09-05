from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    dekad_request_type = fields.Char(string='Request Type')
    dekad_industry = fields.Char(string='Company Field / Industry')
    dekad_employees = fields.Integer(string='Number of Employees')
    dekad_demo_date = fields.Datetime(string='Preferred Demo Date & Time')