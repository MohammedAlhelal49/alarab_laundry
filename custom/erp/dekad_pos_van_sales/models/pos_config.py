from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class POSConfig(models.Model):
    _inherit = 'pos.config'

    is_van_sales = fields.Boolean(string="Is Van Sales", help="Enable Van Sales for this POS")
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string="Fleet Vehicle", help="Select the vehicle for Van Sales")

    @api.constrains('is_van_sales', 'fleet_vehicle_id')
    def _check_fleet_vehicle_required(self):
        for config in self:
            if config.is_van_sales and not config.fleet_vehicle_id:
                raise ValidationError("You must select a Fleet Vehicle when 'Is Van Sales' is enabled.")
            if not config.is_van_sales and config.fleet_vehicle_id:
                raise ValidationError("Fleet Vehicle must be empty when 'Is Van Sales' is disabled.")

    @api.onchange('is_van_sales')
    def _onchange_is_van_sales(self):
        if not self.is_van_sales:
            self.fleet_vehicle_id = False

class POSOrder(models.Model):
    _inherit = 'pos.order'

    van_fleet_vehicle_id = fields.Many2one('fleet.vehicle', string="Van Name", readonly=True)
    van_name = fields.Char(string="Van Name", readonly=True)


    @api.model
    def _process_order(self, order, existing_order):
        """
        Inject custom van fields into the order dict before order is created.
        """
        # Inject van info
        session = self.env['pos.session'].browse(order['session_id'])
        config = session.config_id
        if config.fleet_vehicle_id:
            order['van_fleet_vehicle_id'] = config.fleet_vehicle_id.id
            order['van_name'] = config.fleet_vehicle_id.name

        # Call original method
        return super(POSOrder, self)._process_order(order, existing_order)