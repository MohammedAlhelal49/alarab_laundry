from odoo import models, fields, api
from itertools import groupby as itertools_groupby
from collections import defaultdict
from lxml import etree
import ast
import re


class AnalyticalItemPrintWizard(models.TransientModel):
    _name = 'analytical.item.print.wizard'
    _description = 'Analytical Item Report - Print Wizard'

    analytic_line_ids = fields.Many2many(
        'account.analytic.line',
        string='Analytic Lines',
    )

    group_by = fields.Selection(
        selection='_get_group_by_selection',
        string='Group By',
        required=True,
        default='none',
    )

    show_lines = fields.Boolean(
        string='Show Detail Lines',
        default=False,
        help='If enabled, prints each line inside the group. '
             'If disabled, prints only the group summary rows (like the collapsed UI view).',
    )

    @api.model
    def _get_group_by_selection(self):
        selection = [('none', 'No Grouping')]
        try:
            AnalyticLine = self.env['account.analytic.line']
            result = AnalyticLine.get_view(False, 'search')
            arch = result.get('arch', '')
            if not arch:
                raise ValueError('No arch')

            root = etree.fromstring(arch.encode('utf-8'))

            for node in root.iter('filter'):
                context_str = node.get('context', '')
                if 'group_by' not in context_str:
                    continue
                string = node.get('string', '')
                if not string:
                    continue
                try:
                    ctx = ast.literal_eval(context_str)
                    raw_group = ctx.get('group_by', '')
                except Exception:
                    m = re.search(r"'group_by'\s*:\s*'([^']+)'", context_str)
                    raw_group = m.group(1) if m else ''

                if not raw_group:
                    continue

                key = raw_group.replace(':', '_')
                if not any(k == key for k, _ in selection):
                    selection.append((key, string))

        except Exception:
            selection += [
                ('account_id',         'Analytic Account'),
                ('partner_id',         'Partner'),
                ('product_id',         'Product'),
                ('employee_id',        'Employee'),
                ('general_account_id', 'General Account'),
                ('move_id',            'Journal Entry'),
                ('company_id',         'Company'),
                ('date_month',         'Date: Month'),
                ('date_year',          'Date: Year'),
            ]

        return selection

    def _resolve_field_from_key(self, key):
        date_granularities = {'day', 'week', 'month', 'quarter', 'year'}
        if '_' in key:
            parts = key.rsplit('_', 1)
            if parts[1] in date_granularities:
                return parts[0], parts[1]
        return key, None

    def _group_by_date(self, lines, granularity):
        buckets = defaultdict(list)
        for line in lines:
            if not line.date:
                key = 'Undefined'
            elif granularity == 'day':
                key = line.date.strftime('%Y-%m-%d')
            elif granularity == 'week':
                key = line.date.strftime('%Y-W%W')
            elif granularity == 'month':
                key = line.date.strftime('%Y-%m')
            elif granularity == 'quarter':
                q = (line.date.month - 1) // 3 + 1
                key = f"{line.date.year}-Q{q}"
            elif granularity == 'year':
                key = line.date.strftime('%Y')
            else:
                key = str(line.date)
            buckets[key].append(line)

        LABEL_FORMATS = {
            'day':   '%d %b %Y',
            'week':  'Week %W / %Y',
            'month': '%B %Y',
            'year':  '%Y',
        }

        result = []
        grand_qty = 0.0
        grand_amt = 0.0

        for key in sorted(buckets.keys()):
            group_lines = buckets[key]
            count = len(group_lines)
            sub_qty = sum(l.unit_amount for l in group_lines)
            sub_amt = sum(l.amount for l in group_lines)
            grand_qty += sub_qty
            grand_amt += sub_amt
            if group_lines[0].date and granularity in LABEL_FORMATS:
                label = group_lines[0].date.strftime(LABEL_FORMATS[granularity])
            else:
                label = key
            result.append({
                'label': f"{label} ({count})",
                'lines': group_lines,
                'subtotal_quantity': sub_qty,
                'subtotal_amount': sub_amt,
            })

        return result, grand_qty, grand_amt

    def _get_lines(self):
        if self.analytic_line_ids:
            return self.analytic_line_ids.sorted('date')
        domain = self.env.context.get('active_domain', [])
        return self.env['account.analytic.line'].search(domain, order='date asc')

    def _get_grouped_data(self):
        lines = self._get_lines()
        group_field_key = self.group_by

        if group_field_key == 'none':
            grand_qty = sum(lines.mapped('unit_amount'))
            grand_amt = sum(lines.mapped('amount'))
            return [{
                'label': 'All Items',
                'lines': lines,
                'subtotal_quantity': grand_qty,
                'subtotal_amount': grand_amt,
            }], grand_qty, grand_amt

        field_name, granularity = self._resolve_field_from_key(group_field_key)

        if granularity:
            return self._group_by_date(lines, granularity)

        def _key(line):
            val = line[field_name]
            if hasattr(val, 'id'):
                if val and val.id:
                    return (val.id, val.display_name)
                return (False, 'None')
            return (val, str(val) if val else 'None')

        sorted_lines = sorted(lines, key=_key)
        result = []
        grand_qty = 0.0
        grand_amt = 0.0

        for key, group_iter in itertools_groupby(sorted_lines, key=_key):
            group_lines = list(group_iter)
            count = len(group_lines)
            sub_qty = sum(l.unit_amount for l in group_lines)
            sub_amt = sum(l.amount for l in group_lines)
            grand_qty += sub_qty
            grand_amt += sub_amt
            result.append({
                'label': f"{key[1]} ({count})",
                'lines': group_lines,
                'subtotal_quantity': sub_qty,
                'subtotal_amount': sub_amt,
            })

        return result, grand_qty, grand_amt

    def action_print_pdf(self):
        group_by_labels = dict(self._get_group_by_selection())
        data = {
            'group_by': self.group_by,
            'group_by_label': group_by_labels.get(self.group_by, self.group_by),
            'show_lines': self.show_lines,
        }
        return self.env.ref(
            'dekad_analytic_report.action_report_analytical_item'
        ).report_action(self, data=data)