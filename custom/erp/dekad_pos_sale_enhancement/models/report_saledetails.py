from odoo import models


class ReportSaleDetailsInherit(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def get_sale_details(self, *args, **kwargs):
        # Call original method
        result = super().get_sale_details(*args, **kwargs)

        for category in result.get('products', []):
            for line in category.get('products', []):
                product = self.env['product.product'].browse(line['product_id'])
                line['product_name'] = product.display_name

        for category in result.get('refund_products', []):
            for line in category.get('products', []):
                product = self.env['product.product'].browse(line['product_id'])
                line['product_name'] = product.display_name

        return result
