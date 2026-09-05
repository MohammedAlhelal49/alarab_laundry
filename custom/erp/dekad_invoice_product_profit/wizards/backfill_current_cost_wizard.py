import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BackfillCurrentCostWizard(models.TransientModel):
    """One-off wizard to populate `current_cost` on historic invoice lines
    from the most recent incoming stock.valuation.layer prior to invoice_date.

    Two-step UX:
    - "Preview" fills the read-only preview_ids / summary fields WITHOUT
      writing anything to account.move.line.
    - "Run Backfill" performs the same query and actually writes the values.
    """
    _name = 'invoice.profit.backfill.wizard'
    _description = 'Backfill Historical Invoice Costs'

    candidate_count = fields.Integer(
        string='Candidate Lines',
        readonly=True,
        help="Number of invoice lines currently having NULL current_cost.",
    )
    preview_html = fields.Html(
        string='Preview',
        readonly=True,
        sanitize=False,
    )
    executed = fields.Boolean(readonly=True)

    # ------------------------------------------------------------------
    # Default / open
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        vals['candidate_count'] = self._get_candidate_lines().search_count([])
        return vals

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------
    def _get_candidate_lines(self):
        """Return the recordset of invoice lines eligible for backfill."""
        return self.env['account.move.line'].with_context(active_test=False).search([
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('display_type', '=', 'product'),
            ('current_cost', '=', False),
            ('product_id', '!=', False),
        ], order='move_id, id')

    def _get_posted_datetime(self, move):
        """Return the Datetime when this move actually transitioned to
        state='posted', by scanning its chatter tracking values. Falls
        back to move.create_date if no such tracking entry exists (e.g.
        moves created before Odoo started recording state changes, or
        posted via a code path that suppressed notifications).
        """
        tracking = self.env['mail.tracking.value'].sudo().search([
            ('mail_message_id.model', '=', 'account.move'),
            ('mail_message_id.res_id', '=', move.id),
            ('field_id.name', '=', 'state'),
        ], order='create_date DESC')

        # A move may be reset-to-draft and re-posted several times; take the
        # oldest transition that ended in 'posted' (i.e. the FIRST time it
        # went to posted), so re-posts don't shift the snapshot window.
        for tv in tracking.sorted('create_date'):
            new_val = getattr(tv, 'new_value_char', None) or getattr(tv, 'new_value', None)
            if new_val == 'posted':
                return tv.create_date

        return move.create_date

    def _find_unit_cost(self, line):
        """Resolve the frozen unit cost for one invoice line.

        Returns a tuple (unit_cost, source) where `source` is one of:
          - 'svl'      : taken from the most recent incoming SVL prior to
                         the moment the invoice was posted.
          - 'product'  : taken from product.standard_price for the invoice's
                         company (fallback when no matching SVL exists).
          - None       : no usable value could be found (SVL missing AND
                         product cost is zero); returned as (None, None).
        """
        # -- Attempt 1: SVL prior to the posting moment ---------------------
        cutoff = self._get_posted_datetime(line.move_id)
        if cutoff:
            svl = self.env['stock.valuation.layer'].search([
                ('product_id', '=', line.product_id.id),
                ('company_id', '=', line.move_id.company_id.id),
                ('quantity', '>', 0),
                ('create_date', '<=', cutoff),
            ], order='create_date DESC', limit=1)
            if svl:
                return svl.unit_cost, 'svl'

        # -- Attempt 2: product.standard_price for the invoice's company ---
        product = line.product_id.with_company(line.move_id.company_id)
        cost = product.standard_price
        if cost:
            return cost, 'product'

        return None, None

    def _process(self, commit):
        """Iterate candidate lines and either preview or persist changes.
        Returns a dict with counters + a list of row dicts for the HTML table.
        """
        lines = self._get_candidate_lines()
        rows = []
        updated_from_svl = 0
        updated_from_product = 0
        skipped_no_source = 0
        skipped_no_date = 0

        for line in lines:
            move_name = line.move_id.name or _('/')
            product_name = line.product_id.display_name

            if not self._get_posted_datetime(line.move_id):
                rows.append({
                    'move': move_name,
                    'product': product_name,
                    'source': '',
                    'status': _('SKIPPED — no posted timestamp'),
                    'unit_cost': '',
                })
                skipped_no_date += 1
                continue

            unit_cost, source = self._find_unit_cost(line)
            if unit_cost is None:
                rows.append({
                    'move': move_name,
                    'product': product_name,
                    'source': '',
                    'status': _('SKIPPED — no SVL and product cost is zero'),
                    'unit_cost': '',
                })
                skipped_no_source += 1
                continue

            if commit:
                line.current_cost = unit_cost
            source_label = _('Stock Valuation') if source == 'svl' else _('Product Cost')
            rows.append({
                'move': move_name,
                'product': product_name,
                'source': source_label,
                'status': _('SET') if commit else _('WILL SET'),
                'unit_cost': f'{unit_cost:.4f}',
            })
            if source == 'svl':
                updated_from_svl += 1
            else:
                updated_from_product += 1

        return {
            'rows': rows,
            'total': len(lines),
            'updated_from_svl': updated_from_svl,
            'updated_from_product': updated_from_product,
            'updated': updated_from_svl + updated_from_product,
            'skipped_no_source': skipped_no_source,
            'skipped_no_date': skipped_no_date,
        }

    def _render_preview_html(self, result, mode_label):
        """Build a compact HTML table for preview_html."""
        head = (
            f'<h4>{mode_label}</h4>'
            f'<p><b>{_("Total")}:</b> {result["total"]} &nbsp;·&nbsp; '
            f'<b>{_("From Stock Valuation")}:</b> {result["updated_from_svl"]} &nbsp;·&nbsp; '
            f'<b>{_("From Product Cost")}:</b> {result["updated_from_product"]} &nbsp;·&nbsp; '
            f'<b>{_("Skipped (no source)")}:</b> {result["skipped_no_source"]} &nbsp;·&nbsp; '
            f'<b>{_("Skipped (no date)")}:</b> {result["skipped_no_date"]}</p>'
        )
        table = [
            '<table class="table table-sm table-striped">',
            '<thead><tr>'
            f'<th>{_("Invoice")}</th><th>{_("Product")}</th>'
            f'<th>{_("Unit Cost")}</th><th>{_("Source")}</th>'
            f'<th>{_("Status")}</th>'
            '</tr></thead><tbody>',
        ]
        for row in result['rows']:
            table.append(
                f'<tr><td>{row["move"]}</td><td>{row["product"]}</td>'
                f'<td>{row["unit_cost"]}</td><td>{row["source"]}</td>'
                f'<td>{row["status"]}</td></tr>'
            )
        table.append('</tbody></table>')
        return head + ''.join(table)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_preview(self):
        self.ensure_one()
        result = self._process(commit=False)
        self.preview_html = self._render_preview_html(result, _('Preview (no changes saved)'))
        self.executed = False
        return self._reopen_wizard()

    def action_run(self):
        self.ensure_one()
        result = self._process(commit=True)
        self.preview_html = self._render_preview_html(result, _('Backfill executed'))
        self.executed = True
        _logger.info(
            "dekad_invoice_product_profit backfill: total=%s "
            "from_svl=%s from_product=%s "
            "skipped_no_source=%s skipped_no_date=%s",
            result['total'],
            result['updated_from_svl'], result['updated_from_product'],
            result['skipped_no_source'], result['skipped_no_date'],
        )
        return self._reopen_wizard()

    def _reopen_wizard(self):
        """Keep the wizard open on the same record so the user can see the
        preview / result table."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }