from odoo import fields, models, api

class StockMoveInherited(models.Model):
    _inherit = 'stock.move'

    allowed_location_ids = fields.Many2many(
        'stock.location',
        compute='_compute_allowed_location_ids',
        string='Allowed Source Locations',
    )

    @api.depends('product_id', 'company_id')
    def _compute_allowed_location_ids(self):
        for rec in self:
            company = rec.company_id or self.env.company
            if rec.product_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('company_id', '=', company.id),
                    ('quantity', '>', 0),
                ])
                locations = quants.location_id
            else:
                locations = self.env['stock.location']

            if not locations:
                # Fallback: no stock found for this product (new product / out of
                # stock) -> keep the previous behaviour and show all internal
                # locations of the company instead of leaving the field empty.
                locations = self.env['stock.location'].search([
                    ('usage', '=', 'internal'),
                    ('company_id', '=', company.id),
                ])

            rec.allowed_location_ids = locations

    @api.onchange('product_id')
    def _onchange_product_id_clear_location(self):
        # UI-only: runs when a human edits the line in the form/list, never
        # during automated move creation (sale/purchase rules, MRP, POS...).
        # Scoped to outgoing/internal only: incoming receipts use an
        # external (supplier) source location, and MRP/other flows have
        # their own location logic - clearing there would break them.
        for move in self:
            if move.picking_type_id.code not in ('outgoing', 'internal'):
                continue
            if move.product_id and move.location_id and move.location_id not in move.allowed_location_ids:
                move.location_id = False



