from odoo import models, api


class AnalyticalItemReport(models.AbstractModel):
    _name = 'report.dekad_analytic_report.analytical_item_report'
    _description = 'Analytical Item Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['analytical.item.print.wizard'].browse(docids)
        grouped_data, grand_qty, grand_amt = wizard._get_grouped_data()

        return {
            'wizard': wizard,
            'grouped_data': grouped_data,
            'grand_qty': grand_qty,
            'grand_amt': grand_amt,
            'group_by_label': data.get('group_by_label', ''),
            'group_by': data.get('group_by', ''),
            'company': wizard.env.company,
            'show_lines': data.get('show_lines', False),
        }