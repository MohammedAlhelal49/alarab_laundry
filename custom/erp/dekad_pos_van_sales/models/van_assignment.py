from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VanAssignment(models.Model):
    _name = 'van.assignment'
    _description = 'Van Assignment'
    _sql_constraints = [
        ('unique_van', 'unique(van_id)', 'This van is already assigned. Duplicate vans are not allowed.')
    ]

    van_id = fields.Many2one('fleet.vehicle', string="Van", required=True)
    driver_id = fields.Many2one('res.partner', string="Driver", related='van_id.driver_id', store=True)
    note = fields.Text(string="Note")
    customer_ids = fields.One2many('van.assignment.customer', 'assignment_id', string="Customers")

    customer_names = fields.Text(
        string="Customers",
        compute='_compute_customer_names',
        store=False
    )

    def _compute_customer_names(self):
        for record in self:
            names = record.customer_ids.mapped('partner_id.name')
            record.customer_names = ', '.join(names)

    @api.constrains('customer_ids')
    def _check_customer_constraints(self):
        for rec in self:
            # No customers? Not allowed
            if not rec.customer_ids:
                raise ValidationError("You must assign at least one customer to the van.")

            # Check for duplicates within same van assignment
            seen = set()
            for line in rec.customer_ids:
                if line.partner_id.id in seen:
                    raise ValidationError(
                        f"Customer '{line.partner_id.name}' is duplicated in the same van assignment.")
                seen.add(line.partner_id.id)

            # Check if this customer is assigned to another van assignment
            duplicate_lines = self.env['van.assignment.customer'].search([
                ('partner_id', 'in', rec.customer_ids.mapped('partner_id').ids),
                ('assignment_id', '!=', rec.id)
            ])
            if duplicate_lines:
                names = ', '.join(set(duplicate_lines.mapped('partner_id.name')))
                raise ValidationError(f"The following customers are already assigned to another van: {names}")

    def unlink(self):
        for record in self:
            # Check if van or driver is used in sales orders
            sales_orders = self.env['sale.order'].search([
                '|',
                ('user_id.partner_id.id', '=', record.driver_id.id),
                ('partner_id', 'in', record.customer_ids.mapped('partner_id').ids)
            ])

            if sales_orders:
                raise ValidationError(
                    f"Cannot delete van assignment because this van ('{record.van_id.name}') "
                        "is used in POS orders."
                )

            # Check if the van is used in any POS Order
            if record.van_id:
                pos_orders = self.env['pos.order'].search([
                    ('van_fleet_vehicle_id', '=', record.van_id.id)
                ])
                if pos_orders:
                    raise ValidationError(
                        f"Cannot delete van assignment because this van ('{record.van_id.name}') "
                        "is used in POS orders."
                    )

        return super(VanAssignment, self).unlink()


class VanAssignmentCustomer(models.Model):
    _name = 'van.assignment.customer'
    _description = 'Assigned Customer to Van'

    assignment_id = fields.Many2one('van.assignment', string="Assignment", required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        required=True,
        domain="[('related_user_id', '=', False)]"
    )
    phone = fields.Char(related='partner_id.phone', store=True)
    email = fields.Char(related='partner_id.email', store=True)
    city = fields.Char(related='partner_id.city', store=True)
    country_id = fields.Many2one('res.country', related='partner_id.country_id', store=True)
    user_id = fields.Many2one('res.users', string='Salesperson', related='partner_id.user_id', store=True)
