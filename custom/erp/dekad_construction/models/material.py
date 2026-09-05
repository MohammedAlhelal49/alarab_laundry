from odoo import models, fields, api, _


class Material(models.Model):
    _name = 'material'
    _description = 'Material Line'

    # Link to job cost sheet
    sheet_id = fields.Many2one('job.cost.sheet', required=True, ondelete='cascade')

    # UPDATED: Type selection set to Goods and Services
    type = fields.Selection([
        ('goods', 'Goods'),
        ('services', 'Services')
    ], string='Job Type', default='goods', required=True)

    product_id = fields.Many2one('product.product', string="Product")

    description = fields.Text(string='Description')
    quantity = fields.Float(string='Planned Qty', default=1.0)
    wastage = fields.Float(string='Wastage %', default=0.0)
    quantity_after = fields.Float(compute='_compute_quantity_after_wastage', store=True)
    uom_id = fields.Many2one('uom.uom')
    unit_cost = fields.Monetary()
    cost_price_subtotal = fields.Monetary(compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', related='sheet_id.currency_id', store=True, readonly=True)

    # -----------------------------------------
    #   Cost computations
    # -----------------------------------------

    # FIX: Added 'quantity_after' to the api.depends decorator chain to prevent calculation lag
    @api.depends('quantity_after', 'unit_cost')
    def _compute_subtotal(self):
        for rec in self:
            rec.cost_price_subtotal = rec.quantity_after * rec.unit_cost

    @api.depends('quantity', 'wastage')
    def _compute_quantity_after_wastage(self):
        for rec in self:
            rec.quantity_after = rec.quantity * (1 + rec.wastage / 100)

    # -----------------------------------------
    # Auto-fill from product & Type Reset
    # -----------------------------------------

    @api.onchange('type')
    def _onchange_type(self):
        """Clear out selected product if user switches the job classification type."""
        for rec in self:
            if rec.product_id:
                # If product matches the new filter category, retain it; otherwise, reset.
                is_service = rec.product_id.type == 'service'
                if (rec.type == 'services' and not is_service) or (rec.type == 'goods' and is_service):
                    rec.product_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                # rec.unit_cost = rec.product_id.standard_price

                # Automatically map product names to description line if empty
                if not rec.description:
                    rec.description = rec.product_id.display_name

                if rec.product_id.uom_id:
                    rec.uom_id = rec.product_id.uom_id.id
