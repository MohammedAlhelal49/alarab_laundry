from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_order_confirm_date = fields.Datetime(
        string='Order Confirm Date',
        copy=False,
    )
    x_preparing_order_date = fields.Datetime(
        string='Preparing Order Date',
        copy=False,
    )
    x_shipping_order_date = fields.Datetime(
        string='Shipping Order Date',
        copy=False,
    )
    x_shipment_delivery_date = fields.Datetime(
        string='Shipment Delivery Date',
        copy=False,
    )
    x_shipment_company = fields.Char(
        string='Shipment Company',
        copy=False,
    )
    x_shipment_method = fields.Char(
        string='Shipment Method',
        copy=False,
    )
    x_is_intercompany_dest = fields.Boolean(
        string='Is Intercompany Destination',
        default=False,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            # نرث القيم من الـ move تلقائياً
            if line.move_id:
                move = line.move_id
                line.sudo().with_context(skip_intercompany_sync=True).write({
                    'x_order_confirm_date': move.x_order_confirm_date,
                    'x_preparing_order_date': move.x_preparing_order_date,
                    'x_shipping_order_date': move.x_shipping_order_date,
                    'x_shipment_delivery_date': move.x_shipment_delivery_date,
                    'x_shipment_company': move.x_shipment_company,
                    'x_shipment_method': move.x_shipment_method,
                    'x_is_intercompany_dest': move.x_is_intercompany_dest,
                })
        return records
