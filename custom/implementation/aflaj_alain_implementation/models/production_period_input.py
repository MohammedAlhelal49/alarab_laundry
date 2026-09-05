from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ProductionPeriodInput(models.Model):
    _name = 'production.period.input'
    _description = "production.period.input"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Sequence', readonly=True, store=True, copy=False)
    current_user = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    location_id = fields.Many2one('stock.location', string="Location")
    input_date = fields.Datetime(string="Date", default=fields.datetime.now())
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    stock_picking_ids = fields.One2many("stock.picking", 'production_period_input_id', string="Transfers")
    stock_picking_ids_count = fields.Integer('Transfers count', compute="_compute_stock_picking_ids_count")


    broken_egg_input = fields.Integer(string='Count')
    rejected_egg_input = fields.Integer(string='Count')
    damaged_egg_input = fields.Integer(string='Count')
    mother_egg_input = fields.Integer(string='Count')
    chicken_egg_input = fields.Integer(string='Count')



    @api.model_create_multi
    def create(self, vals_list):
        # Generate a sequence
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('production.period.input')
        records = super(ProductionPeriodInput, self).create(vals_list)
        records.input_production_egg()
        return records

    def write(self, vals):
        res = super().write(vals)
        # --- Dead chicks logic ---
        for rec in self:
            if 'broken_egg_input' in vals  or 'rejected_egg_input' in vals  or 'damaged_egg_input' in vals or 'mother_egg_input' in vals  or 'chicken_egg_input' in vals :
                # --- Validations ---
                if rec.broken_egg_input < 0:
                    raise ValidationError(_("Please enter a proper broken egg input"))

                if rec.rejected_egg_input < 0:
                    raise ValidationError(_("Please enter a proper rejected egg input"))

                if rec.damaged_egg_input < 0:
                    raise ValidationError(_("Please enter a proper damaged egg input"))

                if rec.mother_egg_input < 0:
                    raise ValidationError(_("Please enter a proper mother double egg input"))

                if rec.chicken_egg_input < 0:
                    raise ValidationError(_("Please enter a proper hatching egg input"))

                rec.cancel_stock_picking_ids()
                rec.input_production_egg()
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


    def input_production_egg(self):
        company = self.env.company  # current company

        broken_egg = company.broken_egg
        rejected_egg = company.rejected_egg
        damaged_egg = company.damaged_egg
        mother_egg = company.mother_egg
        chicken_egg = company.chicken_egg
        production_operation = company.production_operation


        # --- Validations ---
        if not broken_egg:
            raise ValidationError(_("Please configure a Broken egg Product in Settings for company %s.") % company.name)

        if not rejected_egg:
            raise ValidationError(_("Please configure a Rejected egg Product in Settings for company %s.") % company.name)

        if not damaged_egg:
            raise ValidationError(
                _("Please configure a Rejected egg Product in Settings for company %s.") % company.name)

        if not mother_egg:
            raise ValidationError(
                _("Please configure a mother double egg Product in Settings for company %s.") % company.name)

        if not chicken_egg:
            raise ValidationError(
                _("Please configure a hatching egg Product in Settings for company %s.") % company.name)



        if not production_operation:
            raise ValidationError(
                _("Please configure a production Operation Type in Settings for company %s.") % company.name)

        for rec in self:
            if not rec.location_id:
                raise ValidationError(_("Please select a location"))
            if rec.broken_egg_input < 0:
                raise ValidationError(_("Please enter a proper broken egg input"))

            if rec.rejected_egg_input < 0:
                raise ValidationError(_("Please enter a proper Rejected egg input"))

            if rec.damaged_egg_input < 0:
                raise ValidationError(_("Please enter a proper damaged egg input"))

            if rec.mother_egg_input < 0:
                    raise ValidationError(_("Please enter a proper mother double egg input"))

            if rec.chicken_egg_input < 0:
                    raise ValidationError(_("Please enter a proper hatching egg input"))

            # --- Receive picking (increase dead chicks) ---
            receive_picking = self.env['stock.picking'].create({
                'production_period_input_id': rec.id,
                'picking_type_id': production_operation.id,
                'location_id': production_operation.default_location_src_id.id,
                'location_dest_id': rec.location_id.id,
                'origin': "Receipt for increasing the production egg generated from production period input %s" % rec.id,
            })
            self.env['stock.move'].create({
                'name': broken_egg.name,
                'product_id': broken_egg.id,
                'product_uom_qty': rec.broken_egg_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': rejected_egg.name,
                'product_id': rejected_egg.id,
                'product_uom_qty': rec.rejected_egg_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })


            self.env['stock.move'].create({
                'name': damaged_egg.name,
                'product_id': damaged_egg.id,
                'product_uom_qty': rec.damaged_egg_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })

            self.env['stock.move'].create({
                'name': mother_egg.name,
                'product_id': mother_egg.id,
                'product_uom_qty': rec.mother_egg_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })



            self.env['stock.move'].create({
                'name': chicken_egg.name,
                'product_id': chicken_egg.id,
                'product_uom_qty': rec.chicken_egg_input,
                'picking_id': receive_picking.id,
                'location_id': receive_picking.location_id.id,
                'location_dest_id': receive_picking.location_dest_id.id,
            })





            receive_picking.action_confirm()
            receive_picking.action_assign()
            receive_picking.button_validate()


class StockPickingInherited(models.Model):
    _inherit = 'stock.picking'
    production_period_input_id = fields.Many2one('production.period.input', string="Production period input")


