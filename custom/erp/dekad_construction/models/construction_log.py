from odoo import models, fields, api
from datetime import datetime

class ConstructionLog(models.Model):
    _name = 'construction.log'
    _description = 'Construction Log'
    _order = 'create_date desc'

    name = fields.Char(string="Description", required=True)
    model_name = fields.Char(string="Model")
    record_ref = fields.Reference(
        selection='_selection_models',
        string="Related Record"
    )
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)
    log_type = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('action', 'Action'),
    ], string="Log Type", default='info')
    timestamp = fields.Datetime(string="Timestamp", default=lambda self: datetime.now())

    @api.model
    def _selection_models(self):
        """Dynamically generate selection for Reference field."""
        models = self.env['ir.model'].search([])
        return [(m.model, m.name) for m in models]

    @api.model
    def create_log(self, description, model_name=None, record=None, log_type='info'):
        """Convenient method for other modules to create logs."""
        self.create({
            'name': description,
            'model_name': model_name,
            'record_ref': f"{model_name},{record.id}" if record else False,
            'log_type': log_type,
        })
