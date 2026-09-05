# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# No cap: all products in the catalog are loaded into the wizard's
# selectable list. Deliberate decision -- be aware this does not scale
# well for very large catalogs (thousands+ of products): expect slower
# load times and a heavier browser render as the catalog grows.


class GmrAddProductsWizard(models.TransientModel):
    _name = 'gmr.add.products.wizard'
    _description = 'Add Multiple Products to a Material Request'

    request_id = fields.Many2one(
        'gmr.request', string='Request', required=True, ondelete='cascade'
    )
    project_id = fields.Many2one(
        related='request_id.project_id', string='Project', readonly=True
    )
    task_id = fields.Many2one(
        'project.task',
        string='Default Task',
        domain="[('project_id', '=', project_id)]",
        help='Default task applied to lines that don\'t have their own '
             'task set yet. Changing this fills in any empty Task cells '
             'below; it does not overwrite a task you already picked on '
             'a specific line.'
    )

    search_name = fields.Char(string='Search Product')

    line_ids = fields.One2many(
        'gmr.add.products.wizard.line', 'wizard_id', string='Products'
    )

    selected_count = fields.Integer(
        string='Selected', compute='_compute_selected_count'
    )

    @api.depends('line_ids.selected')
    def _compute_selected_count(self):
        for wizard in self:
            wizard.selected_count = len(wizard.line_ids.filtered('selected'))

    @api.onchange('task_id')
    def _onchange_task_id(self):
        """Fill the Default Task into any line that doesn't already have
        its own task set. Lines the user already customized individually
        are left untouched."""
        if self.task_id:
            for line in self.line_ids.filtered(lambda l: not l.task_id):
                line.task_id = self.task_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'request_id' in fields_list and not res.get('request_id'):
            res['request_id'] = self.env.context.get('active_id')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        # Populate the product list directly via ORM (not through
        # default_get commands), since passing 500+ o2m rows through the
        # client-side onchange round-trip has proven unreliable and can
        # silently drop field values (e.g. product_id) before the actual
        # save. This runs once, right after the wizard record itself is
        # persisted.
        for wizard in wizards:
            if not wizard.line_ids:
                products = self.env['product.product'].search(
                    [], order='is_favorite desc, name'
                )
                self.env['gmr.add.products.wizard.line'].create([
                    {'wizard_id': wizard.id, 'product_id': product.id,
                     'qty': 1.0, 'selected': False}
                    for product in products
                ])
        return wizards

    def _build_domain(self):
        domain = []
        if self.search_name:
            domain += ['|', ('name', 'ilike', self.search_name),
                        ('default_code', 'ilike', self.search_name)]
        return domain

    def action_search_products(self):
        """Re-filter line_ids using the current search filters. Lines
        already checked (selected) are kept as-is regardless of the
        filter, so the user doesn't lose earlier picks while narrowing
        the list down further."""
        self.ensure_one()
        products = self.env['product.product'].search(
            self._build_domain(), order='is_favorite desc, name'
        )

        already_selected_products = self.line_ids.filtered('selected').product_id
        new_products = products - already_selected_products

        self.line_ids.filtered(lambda l: not l.selected).unlink()
        self.env['gmr.add.products.wizard.line'].create([
            {
                'wizard_id': self.id,
                'product_id': product.id,
                'qty': 1.0,
                'selected': False,
                'task_id': self.task_id.id or False,
            }
            for product in new_products
        ])

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gmr.add.products.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_add_to_request(self):
        self.ensure_one()
        if self.request_id.state != 'draft':
            raise UserError(_('You can only add products while the request is in Draft.'))

        selected_lines = self.line_ids.filtered(lambda l: l.selected and l.qty > 0)
        if not selected_lines:
            raise UserError(_('Please select at least one product with a quantity greater than zero.'))

        if self.request_id.project_id:
            missing_task_lines = selected_lines.filtered(lambda l: not l.task_id)
            if missing_task_lines:
                raise UserError(_(
                    'This request has a Project set, so please select a Task '
                    'for the following selected products: %s'
                ) % ', '.join(missing_task_lines.mapped('product_id.display_name')))

        existing_lines = {
            (line.product_id.id, line.task_id.id): line
            for line in self.request_id.request_line_ids
        }

        for wiz_line in selected_lines:
            key = (wiz_line.product_id.id, wiz_line.task_id.id)
            existing_line = existing_lines.get(key)
            if existing_line:
                existing_line.qty += wiz_line.qty
            else:
                new_line = self.env['gmr.request.line'].create({
                    'request_id': self.request_id.id,
                    'product_id': wiz_line.product_id.id,
                    'qty': wiz_line.qty,
                    'task_id': wiz_line.task_id.id,
                })
                existing_lines[key] = new_line

        return {'type': 'ir.actions.act_window_close'}


class GmrAddProductsWizardLine(models.TransientModel):
    _name = 'gmr.add.products.wizard.line'
    _description = 'Add Multiple Products Wizard Line'

    wizard_id = fields.Many2one(
        'gmr.add.products.wizard', string='Wizard', required=True, ondelete='cascade'
    )
    project_id = fields.Many2one(
        related='wizard_id.project_id', string='Project', readonly=True
    )
    product_id = fields.Many2one('product.product', string='Product', required=True)
    is_favorite = fields.Boolean(related='product_id.is_favorite', string='Favorite', readonly=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id', string='UoM', readonly=True)
    default_code = fields.Char(related='product_id.default_code', string='Reference', readonly=True)
    selected = fields.Boolean(string='Select')
    qty = fields.Float(string='Qty', default=1.0)
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
        help='Task this product line will be linked to on the request.'
    )