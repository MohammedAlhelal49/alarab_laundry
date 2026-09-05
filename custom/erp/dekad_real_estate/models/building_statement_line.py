from odoo import models, fields, api


class BuildingStatementLine(models.Model):
    _name = 'building.statement.line'
    _description = 'Building Statement Line'
    _rec_name = 'contract_number'
    _order = 'rent_end_date desc, id desc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        ondelete='cascade',
        required=True,
        index=True,
    )

    building_id = fields.Many2one(
        'real.estate.buildings',
        string='Building',
        store=True,
    )

    property_id = fields.Many2one(
        'account.analytic.account',
        string='Property',
        store=True,
    )

    contract_number = fields.Char(
        string='Contract No.',
        store=True,
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        store=True,
    )
    rent_start_date = fields.Date(
        string="Contract Start Date",
        store=True,
    )

    rent_end_date = fields.Date(
        string='Contract End Date',
        store=True,
    )

    availability = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Rented'),
    ], string='Status', compute='_compute_availability', store=True)

    payment_type = fields.Selection([
        ('payment', 'Cash'),
        ('pdc', 'Cheque'),
    ], string='Payment Type', required=True, store=True)
    payment_state = fields.Selection([
        ('not_collected', 'غير محصل'),
        ('collected', 'محصل'),
    ], string='Payment Status', store=True,)

    memo = fields.Char(
        string='Payment No.',
    )
    rent_state = fields.Selection(
        related="sale_order_id.rent_state",
        string="Rent State",
        store=True,
        readonly=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        help="account.payment.date for normal payments, "
             "pdc_payment.due_date for PDCs.",
    )

    amount = fields.Monetary(string='Amount', store=True)

    sale_order_amount_untaxed = fields.Monetary(
        string='Contract Amount (Untaxed)',
        related='sale_order_id.amount_untaxed',
        store=True,
    )

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        store=True,
    )

    @api.depends(
        'rent_start_date',
        'rent_end_date',
        'rent_state',
        'sale_order_id.is_closed',
    )
    def _compute_availability(self):
        today = fields.Date.context_today(self)

        for line in self:
            # Closed / churned contract => property is available
            if line.sale_order_id.is_closed:
                line.availability = 'available'

            # Cancelled or not booked => available
            elif line.rent_state in ('not_booked', 'cancel'):
                line.availability = 'available'

            # Active contract and today is within contract period => rented
            elif (
                    line.rent_start_date
                    and line.rent_end_date
                    and line.rent_start_date <= today <= line.rent_end_date
            ):
                line.availability = 'not_available'

            else:
                line.availability = 'available'


    @api.model
    def action_sync_dates(self):
        for line in self.search([]):
            line.write({
                'rent_start_date': line.sale_order_id.rent_start_date,
                'rent_end_date': line.sale_order_id.rent_end_date,
            })
        return True
