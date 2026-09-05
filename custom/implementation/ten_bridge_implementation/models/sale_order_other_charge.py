from odoo import api, fields, models


class SaleOrderOtherCharge(models.Model):
    _name = "sale.order.other.charge"
    _description = "Sale Order Other Charge"
    _order = "due_date, id"

    sale_order_id = fields.Many2one(
        "sale.order",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        related="sale_order_id.company_id",
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        related="sale_order_id.currency_id",
        store=True,
        readonly=True,
    )

    amount = fields.Monetary(
        string="Charge Amount",
        currency_field="currency_id",
        required=True,
    )

    due_date = fields.Date(
        string="Due Date",
        required=True,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        domain="""
            [
                ('company_id', '=', company_id),
                ('type', 'in', ('bank', 'cash'))
            ]
        """,
    )

    available_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line",
        compute="_compute_available_payment_method_line_ids",
    )

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method",
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )

    remarks = fields.Text()

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        for rec in self:
            rec.available_payment_method_line_ids = (
                rec.journal_id.inbound_payment_method_line_ids
                | rec.journal_id.outbound_payment_method_line_ids
            )

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        for rec in self:
            rec.available_payment_method_line_ids = rec.journal_id.outbound_payment_method_line_ids