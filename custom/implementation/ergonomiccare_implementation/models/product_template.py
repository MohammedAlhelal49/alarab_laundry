from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    same_name_product_id = fields.Many2one(
        'product.template',
        string='Duplicate Name Product',
        compute='_compute_same_name_product_id',
        store=True,
    )

    @api.depends('name')
    def _compute_same_name_product_id(self):
        for product in self:
            product.same_name_product_id = False
            if not product.name:
                continue
            duplicate = self.env['product.template'].with_context(active_test=False).sudo().search([
                ('name', '=', product.name),
                ('id', '!=', product.id),
            ], limit=1)
            product.same_name_product_id = duplicate if duplicate else False

    def _log_duplicate_product_to_chatter(self):
        logged_ids = set()
        for product in self:
            if product.id in logged_ids:
                continue
            logged_ids.add(product.id)

            if product.name:
                duplicate = self.env['product.template'].sudo().search([
                    ('name', '=', product.name),
                    ('id', '!=', product.id),
                ], limit=1)
                if duplicate:
                    product.message_post(
                        body=_("Duplicate product name created"),
                        subject=_("Duplicate Information Detected"),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )

    def _check_duplicate_product_policy(self, vals, record=None):
        policy = self.env['ir.config_parameter'].sudo().get_param(
            'ergonomiccare_implementation.duplicate_product_policy', 'warning'
        )
        if policy != 'block':
            return

        name = vals.get('name') if vals.get('name') is not None else (record.name if record else False)
        rid  = record.id if record else 0

        def _fmt(p):
            return p.name or 'No Name'

        if name:
            dup = self.env['product.template'].sudo().search([
                ('name', '=', name),
                ('id', '!=', rid),
            ], limit=1)
            if dup:
                raise ValidationError(
                    _("Duplicate detected:\n- Name already exists: %s") % _fmt(dup)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_duplicate_product_policy(vals)

        self = self.with_context(skip_duplicate_log=True)
        products = super().create(vals_list)
        products._log_duplicate_product_to_chatter()
        return products

    def write(self, vals):
        for rec in self:
            self._check_duplicate_product_policy(vals, record=rec)

        res = super().write(vals)

        if not self.env.context.get('skip_duplicate_log'):
            self._log_duplicate_product_to_chatter()

        return res