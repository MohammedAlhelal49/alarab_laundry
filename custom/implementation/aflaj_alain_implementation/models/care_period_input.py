from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class CarePeriodInput(models.Model):
    _name = 'care.period.input'
    _description = "care.period.input"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Sequence', readonly=True, store=True, copy=False)
    current_user = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    location_id = fields.Many2one('stock.location', string="Location")
    input_date = fields.Datetime(string="Date", default=fields.datetime.now())
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    stock_picking_ids = fields.One2many("stock.picking", 'care_period_input_id', string="Transfers")
    stock_picking_ids_count = fields.Integer('Transfers count', compute="_compute_stock_picking_ids_count")

    dead_chicken_input = fields.Integer(string='Count')
    dead_chicken1_input = fields.Integer(string='Count')
    dead_chicken2_input = fields.Integer(string='Count')
    dead_chicken3_input = fields.Integer(string='Count')
    dead_chicken4_input = fields.Integer(string='Count')

    @api.model_create_multi
    def create(self, vals_list):
        # Generate a sequence
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('care.period.input')
        records = super(CarePeriodInput, self).create(vals_list)
        records.input_dead_chicken()
        return records

    def write(self, vals):
        res = super().write(vals)
        # --- Dead chicks logic ---
        for rec in self:
            if 'dead_chicken_input' in vals or 'dead_chicken1_input' in vals or 'dead_chicken2_input' in vals or 'dead_chicken3_input' in vals or 'dead_chicken4_input' in vals:
                # --- Validations ---
                if rec.dead_chicken_input < 0:
                    raise ValidationError(_("Please enter a proper Dead Chicken input"))

                if rec.dead_chicken1_input < 0:
                    raise ValidationError(_("Please enter a proper dead Production brown chicken input"))

                if rec.dead_chicken2_input < 0:
                    raise ValidationError(_("Please enter a proper dead  Production white chicken input"))

                if rec.dead_chicken3_input < 0:
                    raise ValidationError(_("Please enter a proper dead mother female chicken input"))

                if rec.dead_chicken4_input < 0:
                    raise ValidationError(_("Please enter a proper dead mother female male rooster input"))

                rec.cancel_stock_picking_ids()
                rec.input_dead_chicken()
        return res

    @api.depends('stock_picking_ids')
    def _compute_stock_picking_ids_count(self):
        for rec in self:
            rec.stock_picking_ids_count = len(rec.stock_picking_ids)

    def cancel_stock_picking_ids(self):
        for rec in self:
            for transfer in rec.stock_picking_ids:
                if transfer.state != "done":
                    transfer.unlink()
                else:
                    transfer.action_confirm_cancel()
                    transfer.unlink()

    def action_view_picking(self):
        self.ensure_one()
        action = self.env.ref("stock.action_picking_tree_all").read()[0]

        action["context"] = {'create': True, 'update': False}

        # Just filter by your stock_picking_ids field
        action["domain"] = [("id", "in", self.stock_picking_ids.ids)]

        # If only one picking -> open the form directly
        if len(self.stock_picking_ids) == 1:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = self.stock_picking_ids.id
        return action

    def unlink(self):
        for rec in self:
            rec.cancel_stock_picking_ids()
        return super().unlink()

    def input_dead_chicken(self):
        company = self.env.company  # current company

        chicken = fields.Many2one(
            'product.product', string="Chicken")

        dead_chicken = fields.Many2one(
            'product.product', string="Dead Chicken")

        chicken1 = fields.Many2one(
            'product.product', string="Production brown chicken")

        dead_chicken1 = fields.Many2one(
            'product.product', string="Dead Production brown chicken")

        chicken2 = fields.Many2one(
            'product.product', string="Production white chicken")

        dead_chicken2 = fields.Many2one(
            'product.product', string="Dead Production white chicken")

        chicken3 = fields.Many2one(
            'product.product', string="Mother female  chicken")

        dead_chicken3 = fields.Many2one(
            'product.product', string="Dead Mother female chicken")

        chicken4 = fields.Many2one(
            'product.product', string="Mother female male rooster chicken")

        dead_chicken4 = fields.Many2one(
            'product.product', string="Dead Mother female male rooster chicken")

        chicken = company.chicken
        dead_chicken = company.dead_chicken
        chicken1 = company.chicken1
        dead_chicken1 = company.dead_chicken1
        chicken2 = company.chicken2
        dead_chicken2 = company.dead_chicken2
        chicken3 = company.chicken3
        dead_chicken3 = company.dead_chicken3
        chicken4 = company.chicken4
        dead_chicken4 = company.dead_chicken4

        chicken_operation = company.chicken_operation
        dead_chicken_operation = company.dead_chicken_operation

        # --- Validations ---
        if not chicken or not dead_chicken:
            raise ValidationError(_("Please configure a chicken product for company %s.") % company.name)

        if not chicken1 or not dead_chicken1:
            raise ValidationError(
                _("Please configure a Production brown chicken Product in Settings for company %s.") % company.name)

        if not chicken2 or not dead_chicken2:
            raise ValidationError(
                _("Please configure a Production white chicken Product in Settings for company %s.") % company.name)

        if not chicken3 or not dead_chicken3:
            raise ValidationError(
                _("Please configure a Dead Mother female chicken Product in Settings for company %s.") % company.name)

        if not chicken4 or not dead_chicken4:
            raise ValidationError(
                _("Please configure a Mother female male rooster  Product in Settings for company %s.") % company.name)

        if not chicken_operation or not dead_chicken_operation:
            raise ValidationError(
                _("Please configure a chicken Operation / dead chicken operation in Settings for company %s.") % company.name)

        for rec in self:
            if not rec.location_id:
                raise ValidationError(_("Please select a location"))
            if rec.dead_chicken_input < 0:
                raise ValidationError(_("Please enter a proper Dead Chicken input"))

            if rec.dead_chicken1_input < 0:
                raise ValidationError(_("Please enter a proper dead Production brown chicken input"))

            if rec.dead_chicken2_input < 0:
                raise ValidationError(_("Please enter a proper dead  Production white chicken input"))

            if rec.dead_chicken3_input < 0:
                raise ValidationError(_("Please enter a proper dead mother female chicken input"))

            if rec.dead_chicken4_input < 0:
                raise ValidationError(_("Please enter a proper dead mother female male rooster input"))

            # --- Receive picking (increase dead chicks) ---
            receive_picking = self.env['stock.picking'].create({
                'care_period_input_id': rec.id,
                'picking_type_id': dead_chicken_operation.id,
                'location_id': dead_chicken_operation.default_location_src_id.id,
                'location_dest_id': rec.location_id.id,
                'origin': "Receipt for increasing the dead chicken from the care period input %s" % rec.id,
            })
            self.env['stock.move'].create({
                'name': dead_chicken.name,
                'product_id': dead_chicken.id,
                'product_uom_qty': rec.dead_chicken_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': dead_chicken1.name,
                'product_id': dead_chicken1.id,
                'product_uom_qty': rec.dead_chicken1_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': dead_chicken2.name,
                'product_id': dead_chicken2.id,
                'product_uom_qty': rec.dead_chicken2_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': dead_chicken3.name,
                'product_id': dead_chicken3.id,
                'product_uom_qty': rec.dead_chicken3_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': dead_chicken4.name,
                'product_id': dead_chicken4.id,
                'product_uom_qty': rec.dead_chicken4_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            delivery_picking = self.env['stock.picking'].create({
                'care_period_input_id': rec.id,
                'picking_type_id': chicken_operation.id,
                'location_id': chicken_operation.default_location_src_id.id,
                'location_dest_id': rec.location_id.id,
                'origin': "Delivery for decreasing the chicken from the care period input %s" % rec.id,
            })
            self.env['stock.move'].create({
                'name': chicken.name,
                'product_id': chicken.id,
                'product_uom_qty': rec.dead_chicken_input,
                'quantity' :rec.dead_chicken_input,
                'picking_id': delivery_picking.id,
                'location_id': delivery_picking.location_id.id,
                'location_dest_id': delivery_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': chicken1.name,
                'product_id': chicken1.id,
                'product_uom_qty': rec.dead_chicken1_input,
                'quantity': rec.dead_chicken1_input,
                'picking_id': delivery_picking.id,
                'location_id': delivery_picking.location_id.id,
                'location_dest_id': delivery_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': chicken2.name,
                'product_id': chicken2.id,
                'product_uom_qty': rec.dead_chicken2_input,
                'quantity': rec.dead_chicken2_input,
                'picking_id': delivery_picking.id,
                'location_id': delivery_picking.location_id.id,
                'location_dest_id': delivery_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': chicken3.name,
                'product_id': chicken3.id,
                'product_uom_qty': rec.dead_chicken3_input,
                'quantity': rec.dead_chicken3_input,
                'picking_id': delivery_picking.id,
                'location_id': delivery_picking.location_id.id,
                'location_dest_id': delivery_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': chicken4.name,
                'product_id': chicken4.id,
                'product_uom_qty': rec.dead_chicken4_input,
                'quantity': rec.dead_chicken4_input,
                'picking_id': delivery_picking.id,
                'location_id': delivery_picking.location_id.id,
                'location_dest_id': delivery_picking.location_dest_id.id,
            })
       
            receive_picking.action_confirm()
            receive_picking.action_assign()
            receive_picking.button_validate()
            delivery_picking.action_confirm()
            delivery_picking.action_assign()
            delivery_picking.button_validate()


class StockPickingInherited(models.Model):
    _inherit = 'stock.picking'
    production_period_input_id = fields.Many2one('production.period.input', string="Production period input")
    care_period_input_id = fields.Many2one('care.period.input', string="Care period input")
