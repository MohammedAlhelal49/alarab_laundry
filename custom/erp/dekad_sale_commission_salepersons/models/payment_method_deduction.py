from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleCommissionPaymentMethodLineDeduction(models.Model):
    _name = "sale.commission.payment.method.line.deduction"
    _description = "Commission Deduction by Payment Method Line (Journal)"
    _order = "journal_id, payment_method_line_id, id"

    active = fields.Boolean(default=True)

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        ondelete="restrict",
        domain="[('type','in',('bank','cash','credit'))]",
        help="Select the journal first to filter the payment method names below.",
    )

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method Name",
        required=True,
        ondelete="restrict",
        # only show lines for selected journal AND inbound payment type
        domain="[('journal_id', '=', journal_id), ('payment_type', '=', 'inbound')]",
        help="Choose the Payment Method Line (name) linked to the selected journal. Only incoming methods are shown.",
    )

    payment_method_id = fields.Many2one(
        "account.payment.method",
        string="Payment Method",
        related="payment_method_line_id.payment_method_id",
        store=True,
        readonly=True,
    )
    method_code = fields.Char(
        string="Method Code",
        related="payment_method_line_id.code",
        store=True,
        readonly=True,
    )

    deduction_percent = fields.Float(
        string="Deduction %",
        required=True,
    )

    note = fields.Text(string="Notes")

    _sql_constraints = [
        ("uniq_pml", "unique(payment_method_line_id)", "A rule for this Payment Method Line already exists."),
        ("check_percent_range", "CHECK(deduction_percent >= 0 AND deduction_percent <= 100)",
         "Deduction % must be between 0 and 100."),
    ]

    @api.constrains("journal_id", "payment_method_line_id")
    def _check_journal_and_inbound(self):
        for rec in self:
            if not rec.payment_method_line_id:
                continue
            if rec.payment_method_line_id.journal_id != rec.journal_id:
                raise ValidationError(_(
                    "Selected Payment Method Name belongs to journal '%s', which doesn't match the chosen journal '%s'."
                ) % (rec.payment_method_line_id.journal_id.display_name, rec.journal_id.display_name))
            if rec.payment_method_line_id.payment_type != 'inbound':
                raise ValidationError(_("Only incoming payment methods are allowed."))

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        if self.payment_method_line_id and self.payment_method_line_id.journal_id != self.journal_id:
            self.payment_method_line_id = False