from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection(selection_add=[
        ('6x9', '6 x 9 cm (Custom)')
    ], ondelete={'6x9': 'set default'})

    def _prepare_report_data(self):
        if self.print_format == '6x9':
            if self.custom_quantity <= 0:
                raise UserError(_('You need to set a positive quantity.'))

            xml_id = 'product_label_6x9_new.report_product_template_label_6x9'

            active_model = ''
            products = []
            if self.product_tmpl_ids:
                products = self.product_tmpl_ids
                active_model = 'product.template'
            elif self.product_ids:
                products = self.product_ids
                active_model = 'product.product'

            quantity_dict = {}
            for p in products:
                # FORCE: Ensure we get the barcode string.
                # If p.barcode is False, use an empty string to avoid rendering issues.
                barcode_value = p.barcode or ''
                quantity_dict[str(p.id)] = [(barcode_value, self.custom_quantity)]

            pricelist = self.pricelist_id or self.env['product.pricelist'].search([], limit=1)

            data = {
                'active_model': active_model,
                'quantity': quantity_dict,
                'layout_wizard': self.id,
                'price_included': True,
                'pricelist': pricelist.id,  # Pass the ID for serialization
            }
            return xml_id, data

        return super(ProductLabelLayout, self)._prepare_report_data()