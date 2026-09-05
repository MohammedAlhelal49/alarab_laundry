import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Recompute payment_info_ids for all existing confirmed sale orders.
    Runs automatically after module upgrade via: odoo -u <your_module_name>
    """
    _logger.warning("MIGRATION RUNNING !!!")

    if not version:
        return

    _logger.info(
        "Migration 18.0.1.0.1: recomputing payment_info_ids on existing sale orders..."
    )

    env = api.Environment(cr, SUPERUSER_ID, {})

    orders = env['sale.order'].search([
        ('state', 'in', ['sale', 'cancel']),
    ])

    _logger.info("Found %d confirmed sale orders to recompute.", len(orders))

    if orders:
        # Unlink existing stored lines first to avoid duplicates
        env['sale.order.payment.info'].search([
            ('sale_order_id', 'in', orders.ids)
        ]).unlink()

        # Trigger the compute — because payment_info_ids is store=True,
        # Odoo will persist the result to the database automatically
        orders._compute_payment_info()

    _logger.info("Migration 18.0.1.0.1: payment_info_ids recompute complete.")