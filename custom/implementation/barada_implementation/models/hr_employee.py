from odoo import fields, models


class HrEmployeeGroup(models.Model):
    _name = 'hr.employee.group'
    _description = 'Employee Group'
    _order = 'sequence, name'

    name = fields.Char(
        string='Group Name',
        required=True,
        translate=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
    )

    sequence = fields.Integer(
        default=10,
    )

    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        (
            'employee_group_name_uniq',
            'unique(name)',
            'The employee group name must be unique!'
        ),
    ]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_group_id = fields.Many2one(
        'hr.employee.group',
        string='Employee Group',
        ondelete='restrict',
        tracking=True,
    )