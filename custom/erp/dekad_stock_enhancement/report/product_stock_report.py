from odoo import models

class ProductStockReport(models.AbstractModel):
    _name = 'report.dekad_stock_enhancement.product_stock_report_template'
    _description = 'Product Stock Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['product.product'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
        }
