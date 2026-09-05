from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class GmrCreatePoWizard(models.TransientModel):
    _name = 'gmr.create.po.wizard'
    _description = 'Create Purchase Document Wizard'

    # ==================== Main Fields ====================
    request_ids = fields.Many2many(
        'gmr.request',
        string='Material Requests',
        readonly=True
    )

    request_count = fields.Integer(
        string='Request Count',
        compute='_compute_request_count'
    )

    doc_type = fields.Selection([
        ('po', 'Purchase Order'),
        ('bill', 'Bill Only (No PO)'),
    ], string='Document Type', required=True, default='po')

    doc_type_policy = fields.Selection([
        ('po_only', 'Purchase Order Only'),
        ('bill_only', 'Vendor Bill Only'),
        ('both', 'Both'),
    ], string='Document Type Policy', compute='_compute_doc_type_policy',
        help='Technical field mirroring the configured policy in Settings; '
             'drives whether the Document Type choice is shown at all.')

    can_choose_doc_type = fields.Boolean(
        compute='_compute_doc_type_policy',
        help='Technical field: True only when the policy is "Both", meaning '
             'the Document Type radio is editable rather than locked.'
    )

    doc_type_policy_message = fields.Char(
        compute='_compute_doc_type_policy',
        help='Human-readable explanation of the current restriction, shown '
             'inline in the wizard when the policy is not "Both".'
    )

    @api.depends_context('uid')
    def _compute_doc_type_policy(self):
        policy = self.env['ir.config_parameter'].sudo().get_param(
            'dekad_material_request.doc_type_policy', default='both'
        )
        if policy not in ('po_only', 'bill_only', 'both'):
            policy = 'both'
        allowed_type = self._get_policy_default_doc_type() if policy != 'both' else False
        allowed_label = dict(self._fields['doc_type'].selection).get(allowed_type) if allowed_type else False
        for wizard in self:
            wizard.doc_type_policy = policy
            wizard.can_choose_doc_type = (policy == 'both')
            wizard.doc_type_policy_message = _(
                'Document Type Policy in Settings is restricted to "%s". '
                'Only this type can be created from this wizard.'
            ) % allowed_label if allowed_label else False

    line_ids = fields.One2many(
        'gmr.create.po.wizard.line',
        'wizard_id',
        string='Consolidated Lines'
    )

    document_summary = fields.Text(
        string='Documents to be Created',
        compute='_compute_document_summary',
        help='One document (PO/Bill) is created per distinct vendor found '
             'among the lines below, since a single PO/Bill can only have '
             'one vendor.'
    )

    # ==================== Computed ====================
    @api.depends('request_ids')
    def _compute_request_count(self):
        for record in self:
            record.request_count = len(record.request_ids)

    @api.depends('line_ids.vendor_id', 'line_ids.product_id', 'doc_type')
    def _compute_document_summary(self):
        for wizard in self:
            if not wizard.line_ids:
                wizard.document_summary = ''
                continue

            by_vendor = defaultdict(list)
            missing_vendor_products = []
            for line in wizard.line_ids:
                if line.vendor_id:
                    by_vendor[line.vendor_id].append(line)
                else:
                    missing_vendor_products.append(line.product_id.display_name)

            doc_label = {
                'po': 'Purchase Order',
                'bill': 'Vendor Bill',
            }.get(wizard.doc_type, 'document')

            parts = []
            if by_vendor:
                n = len(by_vendor)
                parts.append(
                    '%d %s%s will be created:' % (
                        n, doc_label, 's' if n > 1 else ''
                    )
                )
                for vendor, vendor_lines in by_vendor.items():
                    parts.append('  \u2022 %s \u2014 %d line(s)' % (vendor.display_name, len(vendor_lines)))

            if missing_vendor_products:
                parts.append('')
                parts.append(
                    '\u26a0 Missing Vendor \u2014 cannot proceed until set on: %s'
                    % ', '.join(missing_vendor_products)
                )

            wizard.document_summary = '\n'.join(parts)

    # ==================== Default Get ====================
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return res

        requests = self.env['gmr.request'].browse(active_ids).exists()
        if not requests:
            raise UserError(_('No valid material requests found.'))

        not_approved = requests.filtered(lambda r: r.state != 'approved')
        if not_approved:
            raise UserError(_(
                'The following requests are not approved:\n%s'
            ) % '\n'.join(not_approved.mapped('name')))

        # Every request must carry the exact same project (including
        # "no project" as its own valid group) -- treating False as
        # just another distinct value, not a wildcard that matches
        # everything. A single PO/Bill can only carry one project_id,
        # so mixing projects here would silently leave it blank.
        distinct_projects = set(requests.mapped(lambda r: r.project_id.id))
        if len(distinct_projects) > 1:
            breakdown = ', '.join(sorted({
                r.project_id.name or _('(no project)') for r in requests
            }))
            raise UserError(_(
                'The selected requests belong to different projects: %s.\n\n'
                'A single PO/Bill can only combine requests from the same '
                'project. Please select requests for one project at a time -- '
                'use "Group By > Project" in the requests list to make this '
                'easier.'
            ) % breakdown)

        res['request_ids'] = [(6, 0, requests.ids)]
        res['doc_type'] = self._get_policy_default_doc_type()
        res['line_ids'] = self._prepare_wizard_lines(requests)
        return res

    @api.model
    def _get_policy_default_doc_type(self):
        param = self.env['ir.config_parameter'].sudo()
        policy = param.get_param('dekad_material_request.doc_type_policy', default='both')
        if policy == 'po_only':
            return 'po'
        if policy == 'bill_only':
            return 'bill'
        default_doc_type = param.get_param('dekad_material_request.default_doc_type', default='po')
        return default_doc_type if default_doc_type in ('po', 'bill') else 'po'

    # ==================== Helpers ====================
    @api.model
    def _effective_vendor(self, line):
        """A request line's own vendor if set, otherwise the request's
        default vendor. Either may be empty."""
        return line.vendor_id or line.request_id.vendor_id

    @api.model
    def _prepare_wizard_lines(self, requests):
        """Consolidate request lines by product + analytic account +
        vendor + task. Vendor is part of the key because a single
        PO/Bill can only carry one vendor -- different vendors must
        never be merged together. Task is part of the key too, so two
        lines for the same product under different tasks stay on
        separate PO/Bill lines (needed for dekad_construction's task_id
        tracking, when that module is installed). Vendor here is only
        an initial suggestion (from the line/request, which is very
        often still empty at this stage); the Admin can set or change
        it directly on the wizard line below."""
        all_lines = requests.mapped('request_line_ids')
        valid_lines = all_lines.filtered(lambda l: l.product_id and l.approved_qty > 0)
        if not valid_lines:
            return []

        product_data = {}
        for line in valid_lines:
            product = line.product_id
            analytic_id = line.request_id.analytic_account_id.id or False
            vendor = self._effective_vendor(line)
            task_id = line.task_id.id or False
            key = (product.id, analytic_id, vendor.id if vendor else False, task_id)

            po_uom = product.uom_po_id or product.uom_id
            qty = line.approved_qty or 0.0
            if line.product_uom_id and line.product_uom_id != po_uom:
                qty = line.product_uom_id._compute_quantity(qty, po_uom)

            if key in product_data:
                product_data[key]['quantity'] += qty
                product_data[key]['_request_ids'].add(line.request_id.id)
            else:
                product_data[key] = {
                    'product_id': product.id,
                    'quantity': qty,
                    'product_uom_id': po_uom.id,
                    'analytic_account_id': analytic_id,
                    'vendor_id': vendor.id if vendor else False,
                    'task_id': task_id,
                    'price_unit': 0.0,
                    '_request_ids': {line.request_id.id},
                }

        result = []
        for data in product_data.values():
            request_ids = data.pop('_request_ids')
            data['request_ids'] = [(6, 0, list(request_ids))]
            # Suggest a price when a vendor is already known -- pure UX,
            # the Admin can always override it.
            if data['vendor_id']:
                product = self.env['product.product'].browse(data['product_id'])
                seller = product._select_seller(
                    partner_id=self.env['res.partner'].browse(data['vendor_id']),
                    quantity=data['quantity'],
                    date=fields.Date.today(),
                )
                data['price_unit'] = seller.price if seller else (product.standard_price or 0.0)
            result.append((0, 0, data))
        return result

    # ==================== Action ====================
    def action_create_document(self):
        """Create one PO and/or Bill per distinct vendor found among
        self.line_ids -- reads vendor/price exactly as currently shown
        in the wizard (including anything the Admin just typed in),
        never recomputed from the source requests."""
        self.ensure_one()

        if not self.request_ids:
            raise UserError(_('No material requests found.'))

        allowed_doc_type = self._get_policy_default_doc_type() if self.doc_type_policy != 'both' else None
        if allowed_doc_type and self.doc_type != allowed_doc_type:
            chosen_label = dict(self._fields['doc_type'].selection).get(self.doc_type)
            allowed_label = dict(self._fields['doc_type'].selection).get(allowed_doc_type)
            policy_label = dict(self._fields['doc_type_policy'].selection).get(self.doc_type_policy)
            raise UserError(_(
                'You selected "%(chosen)s", but the Document Type Policy in '
                'Settings is currently set to "%(policy)s". Only "%(allowed)s" '
                'can be created from this wizard.\n\n'
                'Go to Material Requests > Settings to change the policy, or '
                'select "%(allowed)s" here instead.'
            ) % {
                'chosen': chosen_label,
                'policy': policy_label,
                'allowed': allowed_label,
            })

        if not self.line_ids:
            raise UserError(_('No valid product lines found.'))

        missing_vendor = self.line_ids.filtered(lambda l: not l.vendor_id)
        if missing_vendor:
            names = ', '.join(missing_vendor.mapped('product_id.display_name'))
            raise UserError(_(
                'Please set a Vendor for: %s'
            ) % names)

        lines_without_price = self.line_ids.filtered(lambda l: not l.price_unit)
        if lines_without_price:
            names = ', '.join(lines_without_price.mapped('product_id.display_name'))
            raise UserError(_('Please set a price for: %s') % names)

        # Group by vendor -- one document per vendor. If the Admin set
        # the same vendor on rows that started out with different
        # vendors (or none), they now correctly merge into one document.
        by_vendor = defaultdict(list)
        for wl in self.line_ids:
            by_vendor[wl.vendor_id].append(wl)

        po_ids, bill_ids = [], []
        for vendor, wiz_lines in by_vendor.items():
            vendor_requests = self.env['gmr.request']
            for wl in wiz_lines:
                vendor_requests |= wl.request_ids

            if self.doc_type == 'po':
                po = self._create_purchase_order(vendor, vendor_requests, wiz_lines)
                po_ids.append(po.id)
            else:
                bill = self._create_bill_only(vendor, vendor_requests, wiz_lines)
                bill_ids.append(bill.id)

        if self.doc_type == 'po':
            return self._open_records('purchase.order', po_ids, _('Purchase Order'), _('Purchase Orders'))
        else:
            return self._open_records('account.move', bill_ids, _('Vendor Bill'), _('Vendor Bills'))

    def _open_records(self, model, ids, singular_name, plural_name):
        """Open the single created record directly, or a list view if
        several documents (one per vendor) were created at once."""
        if len(ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': singular_name,
                'res_model': model,
                'res_id': ids[0],
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': plural_name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('id', 'in', ids)],
            'target': 'current',
        }

    def _build_po_lines(self, wiz_lines, vendor):
        """Build PO order_line vals from wizard lines, all for one vendor."""
        po_line_has_task = 'task_id' in self.env['purchase.order.line']._fields
        po_lines = []
        for wl in wiz_lines:
            product = wl.product_id
            if hasattr(product, 'get_product_multiline_description_purchase'):
                name = product.get_product_multiline_description_purchase()
            else:
                name = product.display_name or product.name

            seller = product._select_seller(
                partner_id=vendor,
                quantity=wl.quantity,
                date=fields.Date.today(),
            )
            date_planned = fields.Datetime.now() + timedelta(
                days=seller.delay if seller and seller.delay else 1
            )
            analytic_distribution = {str(wl.analytic_account_id.id): 100} if wl.analytic_account_id else False

            line_vals = {
                'product_id': product.id,
                'name': name,
                'product_qty': wl.quantity,
                'product_uom': wl.product_uom_id.id,
                'price_unit': wl.price_unit,
                'date_planned': date_planned,
                'analytic_distribution': analytic_distribution,
            }
            if po_line_has_task and wl.task_id:
                line_vals['task_id'] = wl.task_id.id

            po_lines.append((0, 0, line_vals))
        return po_lines

    @api.model
    def _requests_common_project(self, requests):
        """A single project.project only if every contributing request
        shares the exact same one -- never guess when they differ."""
        projects = requests.mapped('project_id')
        return projects if len(projects) == 1 else self.env['project.project']

    def _create_purchase_order(self, vendor, requests, wiz_lines):
        """Create a PO for one vendor -- user continues flow manually."""
        po_vals = {
            'partner_id': vendor.id,
            'origin': ', '.join(requests.mapped('name')),
            'order_line': self._build_po_lines(wiz_lines, vendor),
            'gmr_request_ids': [(6, 0, requests.ids)],
        }
        if 'project_id' in self.env['purchase.order']._fields:
            project = self._requests_common_project(requests)
            if project:
                po_vals['project_id'] = project.id

        po = self.env['purchase.order'].create(po_vals)

        requests.with_context(
            mail_notrack=True,
            tracking_disable=True,
        ).write({
            'state': 'po_created',
            'purchase_order_ids': [(4, po.id)],
        })
        return po

    def _get_bill_account(self, product, company):
        """Resolve the expense/COGS account for a bill line, with a
        safer fallback chain than picking an arbitrary company account:
        1. product's own accounting configuration
        2. product category's expense account
        3. a configured default (ir.config_parameter, optional)
        4. last resort: any expense/liability_current account for the
           company (previous behavior, kept as a final fallback only)
        """
        accounts = product.product_tmpl_id.get_product_accounts()
        account = accounts.get('expense') or accounts.get('stock_input')
        if not account:
            account = product.categ_id.property_account_expense_categ_id
        if not account:
            param = self.env['ir.config_parameter'].sudo().get_param(
                'dekad_material_request.default_expense_account_id'
            )
            if param and str(param).isdigit():
                account = self.env['account.account'].browse(int(param)).exists()
        if not account:
            account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', 'in', ['expense', 'liability_current']),
            ], limit=1)
        return account

    def _create_bill_only(self, vendor, requests, wiz_lines):
        """Create a Vendor Bill directly for one vendor, with no
        Purchase Order at all. Useful for small/urgent purchases where
        going through a full PO cycle isn't warranted."""
        company = self.env.company
        aml_has_task = 'task_id' in self.env['account.move.line']._fields

        bill_lines = []
        for wl in wiz_lines:
            product = wl.product_id
            account = self._get_bill_account(product, company)
            analytic_distribution = (
                {str(wl.analytic_account_id.id): 100} if wl.analytic_account_id else False
            )

            line_vals = {
                'product_id': product.id,
                'name': product.get_product_multiline_description_purchase()
                        if hasattr(product, 'get_product_multiline_description_purchase')
                        else (product.display_name or product.name),
                'quantity': wl.quantity,
                'product_uom_id': wl.product_uom_id.id,
                'price_unit': wl.price_unit,
                'account_id': account.id if account else False,
                'analytic_distribution': analytic_distribution,
            }
            if aml_has_task and wl.task_id:
                line_vals['task_id'] = wl.task_id.id

            bill_lines.append((0, 0, line_vals))

        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_origin': ', '.join(requests.mapped('name')),
            'invoice_line_ids': bill_lines,
            'company_id': company.id,
        }
        if 'project_id' in self.env['account.move']._fields:
            project = self._requests_common_project(requests)
            if project:
                bill_vals['project_id'] = project.id

        bill = self.env['account.move'].create(bill_vals)

        requests.with_context(
            mail_notrack=True,
            tracking_disable=True,
        ).write({
            'state': 'bill_created',
            'account_move_ids': [(4, bill.id)],
        })
        return bill


class GmrCreatePoWizardLine(models.TransientModel):
    _name = 'gmr.create.po.wizard.line'
    _description = 'Create PO Wizard Line'

    wizard_id = fields.Many2one(
        'gmr.create.po.wizard',
        string='Wizard',
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )

    quantity = fields.Float(
        string='Total Quantity',
        default=0.0
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit'
    )

    price_unit = fields.Float(
        string='Unit Price',
        default=0.0
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        readonly=True,
        help='Task from the source request line. Passed through to the '
             'PO/Bill line as task_id if dekad_construction (or another '
             'module providing that field) is installed; harmless '
             'otherwise.'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]",
        help='Vendor to use for this line when creating the PO/Bill. '
             'Pre-filled from the request line\'s own Vendor, or the '
             'request\'s default Vendor, if either was already set -- '
             'often still empty at this stage since Vendor is normally '
             'decided here by the Admin. Editable.'
    )

    request_ids = fields.Many2many(
        'gmr.request',
        string='Source Requests',
        readonly=True,
        help='Material Requests that contributed to this consolidated '
             'line. Kept from consolidation time so the created PO/Bill '
             'links back to the right requests even if Vendor is changed '
             'here afterward.'
    )

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Suggest a price from the vendor's seller info once a Vendor
        is picked here. Only fills an empty price -- never overwrites a
        price the Admin already typed in."""
        if self.vendor_id and self.product_id and not self.price_unit:
            seller = self.product_id._select_seller(
                partner_id=self.vendor_id,
                quantity=self.quantity,
                date=fields.Date.today(),
            )
            self.price_unit = seller.price if seller else (self.product_id.standard_price or 0.0)