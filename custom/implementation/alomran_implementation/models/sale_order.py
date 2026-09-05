from odoo import models, fields,api,_
from odoo.exceptions import ValidationError


class ScheduleDay(models.Model):
    _name = 'schedule.day'
    _description = 'Schedule Day'

    name = fields.Char(required=True)

class CourseDurationUnit(models.Model):
    _name = 'course.duration.units'
    _description = 'Course Duration Unit'

    name = fields.Char(string='Name', required=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    course_duration_units = fields.Many2many(
        'course.duration.units',
        string='Course Duration Units'
    )

    registration_type = fields.Selection([
        ('online', 'Online'),
        ('in_person', 'In person')
    ], string='Registration type')

    schedule_day = fields.Many2many(
        'schedule.day',
        string='Schedule Days'
    )
    payment_method = fields.Selection([
        ('tabby', 'Tabby'),
        ('tamara', 'Tamara'),
        ('visa', 'Visa'),
        ('cash', 'Cash')
    ], string='Payment Method')

    time = fields.Integer(string='Time')

    study_method = fields.Selection([
        ('vip', 'VIP'), ('group', 'GROUP')
    ], string='Study method')

    source = fields.Selection([
        ('hot_call', 'Hot Call'),
        ('social_media', 'Social Media'),
        ('walk_in', 'Walk-in'),
        ('referral', 'Referral'),
        ('legacy_data', 'Legacy Data')
    ], string='Source')

    enrollment_type = fields.Selection([
        ('new', 'New'), ('re_enrollment', 'Re-enrollment')
    ], string='Enrollment Type')

    quotation_note = fields.Char(string='Note')

    course_duration_value = fields.Integer(string='Course Duration Value')


    starting_course_date = fields.Date(string='Starting Course Date')

    # Contract date (editable), set automatically on save if empty
    contract_date = fields.Datetime(
        string='Contract Date',
        copy=False, default=fields.datetime.now()
    )

    admin_signature = fields.Image(
        string="Admin Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024)

    admin_signed_by = fields.Char(
        string="Admin Signed By", copy=False)

    admin_signed_on = fields.Datetime(
        string="Admin Signed On", copy=False)


    admin_approval = fields.Selection([
        ('pending', 'Pending'), ('rejected', 'Rejected'), ('approved', 'Approved')
    ], string='Admin Approval' , default = "pending" , tracking=True)

    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute='_compute_remaining_amount',
        currency_field='currency_id',
        store=True,
        help="The remaining amount to be invoiced (Total Amount - Invoiced Amount)."

    )

    initial_payment = fields.Float(string="Initial Payment")
    balance = fields.Float(string="Balance", compute='_compute_balance', store=True)

    second_payment_amount = fields.Float(string="Second Payment Amount")
    second_payment_date = fields.Date(string="Second Payment Date")

    @api.depends('amount_total', 'initial_payment')
    def _compute_balance(self):
        for order in self:
            order.balance = (order.amount_total or 0.0) - (order.initial_payment or 0.0)

    @api.depends('amount_total', 'amount_invoiced')
    def _compute_remaining_amount(self):
        for order in self:
            order.remaining_amount = order.amount_total - order.amount_invoiced

    @api.onchange('admin_signature')
    def _onchange_admin_signature(self):
        for order in self:
            if order.admin_signature and not order.admin_signed_on:
                order.admin_signed_on = fields.Datetime.now()
                order.admin_signed_by = self.env.user.name

    # # Override the confirmation action to ensure a customer signature is present
    # def action_confirm(self):
    #     for order in self:
    #         if not order.signature:
    #             raise ValidationError(_("You cannot confirm this Sale Order without a customer signature."))
    #     return super(SaleOrder, self).action_confirm()

    from odoo import api, fields, models, _
    from odoo import models, fields, api
    from decimal import Decimal
    from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

    VAT_RATE = Decimal('0.05')  # UAE 5% VAT

    class SaleOrderLine(models.Model):
        _inherit = "sale.order.line"
        amount_delivered = fields.Float(
            string='Qty Delivered Amount', digits='Amount Delivered',
            compute="_compute_amount_delivered", readonly=True, store=True)

        amount_to_deliver = fields.Float(compute='_compute_amount_to_deliver', string='Qty To Deliver Amount',
                                         store=True,
                                         readonly=True,
                                         digits='Amount to deliver')

        @api.depends('qty_delivered', 'price_unit')
        def _compute_amount_delivered(self):
            for rec in self:
                rec.amount_delivered = rec.qty_delivered * rec.price_unit

        @api.depends('qty_to_deliver', 'price_unit')
        def _compute_amount_to_deliver(self):
            for rec in self:
                rec.amount_to_deliver = rec.qty_to_deliver * rec.price_unit

        price_unit_vat = fields.Monetary(
            string="Unit Price (incl. VAT)",
            compute="_compute_price_unit_vat",
            store=False,
            currency_field="currency_id",
            help="Unit price including VAT. Editing this field updates the Unit Price (excl. VAT).",
        )

        # ------------------------------
        # Compute price_unit_vat dynamically from price_unit
        # ------------------------------
        @api.depends("price_unit", "tax_id")
        def _compute_price_unit_vat(self):
            for line in self:
                price_ex = line.price_unit or 0.0

                if not line.tax_id:
                    line.price_unit_vat = price_ex
                    continue

                taxes = line.tax_id.compute_all(
                    price_ex,
                    currency=line.order_id.currency_id,
                    quantity=1,
                    product=line.product_id,
                    partner=line.order_id.partner_id,
                )
                line.price_unit_vat = taxes["total_included"]
