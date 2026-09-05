from odoo import models, fields, api


class RequiredFieldConfig(models.Model):
    _name = 'required.field.config'
    _description = 'Dynamic Required Field'
    _rec_name = 'field_id'

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade'
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        domain="[('model_id', '=', model_id)]",
        ondelete='cascade'
    )


    required = fields.Boolean(
        string='Required'
    )

    duplicate_warning = fields.Boolean(
        string='Duplicate Warning'
    )
    prevent_duplicate = fields.Boolean(
        string='Prevent Duplicate'
    )

    _sql_constraints = [
        (
            'unique_model_field',
            'unique(model_id, field_id)',
            'Field already configured.'
        )
    ]

