# =========================================================================
# >>> NEW FILE — ADDED FOR SUBCONTRACTOR RETENTION & BILLING FEATURE <<<
# This whole file is new; it did NOT exist in the original module.
#
# Two company-level settings:
# - subcontractor_service_account_id: the Expense Account used on the
#   auto-created "Subcontracting Service" product for each task (see
#   project_milestone.py action_create_subcontractor_bill).
# - retention_product_id: the Product used as the invoice line for the
#   retention deduction. Its own Expense Account determines the accounting
#   entry (should point to your Retention Payable liability account).
# =========================================================================
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    subcontractor_service_account_id = fields.Many2one(
        'account.account',
        string="Subcontractor Service Account",
        company_dependent=True,
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        help="Expense account used when auto-creating the Subcontracting "
             "Service product for a task's first bill.",
    )

    retention_product_id = fields.Many2one(
        'product.product',
        string="Retention Product",
        company_dependent=True,
        domain="[('type', '=', 'service')]",
        help="Service product used as the invoice line for the retention "
             "withheld. Its Expense Account should point to the Retention "
             "Payable liability account.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    subcontractor_service_account_id = fields.Many2one(
        related='company_id.subcontractor_service_account_id',
        string="Subcontractor Service Account",
        readonly=False,
    )

    retention_product_id = fields.Many2one(
        related='company_id.retention_product_id',
        string="Retention Product",
        readonly=False,
    )