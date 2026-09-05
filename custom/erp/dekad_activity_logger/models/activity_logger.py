import json
from odoo import models, fields, api


class ActivityLogger(models.Model):
    _name = 'activity.logger'
    _description = 'System Activity Logger'
    _order = 'create_date desc'

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    model_id = fields.Many2one('ir.model', string="Model (Section)", required=True, index=True, ondelete='cascade')
    record_id = fields.Integer(string="Record ID", required=True, index=True)
    record_name = fields.Char(string="Record Name")
    operation_type = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
    ], string="Action Type", required=True, index=True)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)
    changes_json = fields.Text(string="Changes (JSON)")
    formatted_changes = fields.Html(string="Formatted Changes", compute='_compute_formatted_changes', sanitize=False)
    log_source = fields.Selection([
        ('user', 'User Change'),
        ('system', 'System Change'),
    ], default='user', required=True, index=True)
    document_type = fields.Char(
        string="Document Type",
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        index=True,
        default=lambda self: self.env.company,
    )
    record_ref = fields.Reference(
        string="Record Name",
        selection='_selection_target_models',
        compute='_compute_record_ref',
        store=True,
        readonly=True,
    )

    invoice_line_ids = fields.One2many(
        'activity.logger.invoice.line',
        'logger_id',
        string='Invoice Lines'
    )

    old_invoice_line_ids = fields.One2many(
        'activity.logger.invoice.line',
        'logger_id',
        compute='_compute_invoice_line_views',
    )

    new_invoice_line_ids = fields.One2many(
        'activity.logger.invoice.line',
        'logger_id',
        compute='_compute_invoice_line_views',
    )
    invoice_lines_json = fields.Text()

    invoice_lines_html = fields.Html(
        compute='_compute_invoice_lines_html',
        sanitize=False,
    )

    has_invoice_lines = fields.Boolean(
        compute='_compute_has_invoice_lines'
    )

    @api.depends(
        'invoice_line_ids',
        'old_invoice_line_ids',
        'new_invoice_line_ids',
        'invoice_lines_json',
    )
    def _compute_has_invoice_lines(self):
        for rec in self:
            rec.has_invoice_lines = bool(
                rec.invoice_line_ids
                or rec.old_invoice_line_ids
                or rec.new_invoice_line_ids
                or rec.invoice_lines_json
            )

    def _compute_invoice_lines_html(self):
        for rec in self:

            if not rec.invoice_lines_json:
                rec.invoice_lines_html = ''
                continue

            lines = json.loads(
                rec.invoice_lines_json
            )

            # Journal Entries
            if rec.document_type == 'Journal Entry':

                html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Account</th>
                            <th>Partner</th>
                            <th>Label</th>
                            <th>Analytic</th>
                            <th>Taxes</th>
                            <th>Debit</th>
                            <th>Credit</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                for line in lines:
                    html += f"""
                    <tr>
                        <td>{line.get('account', '')}</td>
                        <td>{line.get('partner', '')}</td>
                        <td>{line.get('label', '')}</td>
                        <td>{line.get('analytic', '')}</td>
                        <td>{line.get('taxes', '')}</td>
                        <td>{line.get('debit', '')}</td>
                        <td>{line.get('credit', '')}</td>
                    </tr>
                    """

            # Customer/Vendor Invoices
            elif rec.document_type in (
                    'Customer Invoice',
                    'Vendor Bill',
                    'Customer Credit Note',
                    'Vendor Credit Note',
                    'Sales Receipt',
                    'Purchase Receipt',
            ):

                html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Account</th>
                            <th>Analytic</th>
                            <th>Quantity</th>
                            <th>UoM</th>
                            <th>Price</th>
                            <th>Taxes</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                for line in lines:
                    html += f"""
                    <tr>
                        <td>{line.get('product', '')}</td>
                        <td>{line.get('account', '')}</td>
                        <td>{line.get('analytic', '')}</td>
                        <td>{line.get('quantity', '')}</td>
                        <td>{line.get('uom', '')}</td>
                        <td>{line.get('price', '')}</td>
                        <td>{line.get('taxes', '')}</td>
                        <td>{line.get('amount', '')}</td>
                    </tr>
                    """

            # Sales Orders / Purchase Orders
            elif rec.document_type in (
                    'Sales Order',
                    'Purchase Order',
            ):

                html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Analytic Distribution</th>
                            <th>Quantity</th>
                            <th>UoM</th>
                            <th>Price</th>
                            <th>Taxes</th>
                            <th>Discount</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                for line in lines:
                    html += f"""
                    <tr>
                        <td>{line.get('product', '')}</td>
                        <td>{line.get('analytic_distribution', '')}</td>
                        <td>{line.get('quantity', '')}</td>
                        <td>{line.get('uom', '')}</td>
                        <td>{line.get('price', '')}</td>
                        <td>{line.get('taxes', '')}</td>
                        <td>{line.get('discount', '')}</td>
                        <td>{line.get('amount', '')}</td>
                    </tr>
                    """

            # Deliveries
            elif rec.document_type == 'Deliveries':

                html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Source Location</th>
                            <th>Product</th>
                            <th>Final Location</th>
                            <th>Date Scheduled</th>
                            <th>Deadline</th>
                            <th>Packaging</th>
                            <th>Demand</th>
                            <th>Analytic</th>
                            <th>Unit Cost</th>
                            <th>Cost Amount</th>
                            <th>UoM</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                for line in lines:
                    html += f"""
                    <tr>
                        <td>{line.get('location', '')}</td>
                        <td>{line.get('product', '')}</td>
                        <td>{line.get('location_dest', '')}</td>
                        <td>{line.get('date', '')}</td>
                        <td>{line.get('date_deadline', '')}</td>
                        <td>{line.get('packaging', '')}</td>
                        <td>{line.get('quantity', '')}</td>
                        <td>{line.get('analytic', '')}</td>
                        <td>{line.get('unit_cost', '')}</td>
                        <td>{line.get('amount', '')}</td>
                        <td>{line.get('uom', '')}</td>
                    </tr>
                    """

            else:
                rec.invoice_lines_html = ''
                continue

            html += """
                    </tbody>
                </table>
            """

            rec.invoice_lines_html = html


    @api.depends('invoice_line_ids')
    def _compute_invoice_line_views(self):

        for rec in self:
            rec.old_invoice_line_ids = (
                rec.invoice_line_ids.filtered(
                    lambda l: l.snapshot_type == 'old'
                )
            )

            rec.new_invoice_line_ids = (
                rec.invoice_line_ids.filtered(
                    lambda l: l.snapshot_type == 'new'
                )
            )


    @api.model
    def _selection_target_models(self):
        models = self.env['ir.model'].search([])
        return [(m.model, m.name) for m in models]

    @api.depends('model_id', 'record_id')
    def _compute_record_ref(self):
        for rec in self:
            rec.record_ref = False

            if not rec.model_id or not rec.record_id:
                continue

            model_name = rec.model_id.model

            if model_name not in self.env:
                continue

            target = self.env[model_name].browse(rec.record_id)

            if target.exists():
                rec.record_ref = target

    @api.depends(
        'document_type',
        'model_id',
        'operation_type',
        'record_name',
        'record_id'
    )
    def _compute_name(self):
        operation_labels = {
            'create': 'Created',
            'write': 'Updated',
            'unlink': 'Deleted',
        }

        for rec in self:
            model = rec.model_id.exists()

            display_name = (
                    rec.document_type
                    or (model.name if model else 'Unknown Model')
            )

            rec.name = (
                f"{operation_labels.get(rec.operation_type, rec.operation_type)} - "
                f"{display_name} "
                f"({rec.record_name or rec.record_id})"
            )


    @api.depends(
        'changes_json',
        'operation_type',
        'user_id',
        'document_type',
        'record_name',
        'create_date'
    )
    def _compute_formatted_changes(self):
        for rec in self:

            if not rec.changes_json:
                rec.formatted_changes = (
                    "<p class='text-muted'>No detailed changes recorded.</p>"
                )
                continue

            try:
                changes = json.loads(rec.changes_json)

                badge_class = {
                    'create': 'success',
                    'write': 'warning',
                    'unlink': 'danger',
                }.get(rec.operation_type, 'info')

                user = rec.user_id.exists()

                user_name = (
                    user.display_name
                    if user
                    else '(Deleted User)'
                )

                html = f"""
                    <div class="alert alert-{badge_class}">
                        <h4 style="margin-bottom:10px;">
                            {dict(rec._fields['operation_type'].selection).get(rec.operation_type)}
                        </h4>

                        <strong>User:</strong> {user_name}<br/>
                        <strong>Document:</strong> {rec.document_type or ''}<br/>
                        <strong>Record:</strong> {rec.record_name or ''}<br/>
                        <strong>Date:</strong> {rec.create_date or ''}
                    </div>
                """

                # DELETE
                if rec.operation_type == 'unlink':

                    html += """
                        <div class="alert alert-danger">
                            Record deleted successfully.
                        </div>

                        <table class="table table-sm table-bordered">
                            <thead>
                                <tr>
                                    <th>Field</th>
                                    <th>Value Before Deletion</th>
                                </tr>
                            </thead>
                            <tbody>
                    """

                    for field, values in changes.items():
                        old_val = values.get('old', '')

                        html += f"""
                            <tr>
                                <td><strong>{field}</strong></td>
                                <td>{old_val}</td>
                            </tr>
                        """

                    html += """
                            </tbody>
                        </table>
                    """

                    rec.formatted_changes = html
                    continue


                # CREATE
                if rec.operation_type == 'create':

                    html += """
                        <table class="table table-sm table-bordered">
                            <thead>
                                <tr>
                                    <th>Field</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
                    """

                    for field, values in changes.items():

                        value = values.get('new', '')

                        if value in (
                                False,
                                '',
                                'False',
                                'None',
                                None
                        ):
                            continue

                        html += f"""
                            <tr>
                                <td><strong>{field}</strong></td>
                                <td>{value}</td>
                            </tr>
                        """

                    html += """
                            </tbody>
                        </table>
                    """

                    rec.formatted_changes = html
                    continue

                # UPDATE
                html += """
                    <table class="table table-sm table-bordered">
                        <thead>
                            <tr>
                                <th>Changed Field</th>
                                <th>Previous Value</th>
                                <th>New Value</th>
                            </tr>
                        </thead>
                        <tbody>
                """

                for field, values in changes.items():

                    old_val = values.get('old') or '(Empty)'
                    new_val = values.get('new') or '(Empty)'

                    if str(old_val) == str(new_val):
                        continue

                    html += f"""
                        <tr>
                            <td><strong>{field}</strong></td>
                            <td>
                                <span class="text-danger">
                                    {old_val}
                                </span>
                            </td>
                            <td>
                                <span class="text-success">
                                    {new_val}
                                </span>
                            </td>
                        </tr>
                    """

                html += """
                        </tbody>
                    </table>
                """

                rec.formatted_changes = html

            except Exception:
                rec.formatted_changes = (
                    "<i class='text-danger'>Failed to parse changes.</i>"
                )

class ActivityLoggerInvoiceLine(models.Model):
    _name = 'activity.logger.invoice.line'
    _description = 'Activity Logger Invoice Line'


    logger_id = fields.Many2one(
        'activity.logger',
        required=True,
        ondelete='cascade'
    )

    snapshot_type = fields.Selection([
        ('old', 'Old'),
        ('new', 'New'),
    ])

    product = fields.Char()
    account = fields.Char()
    analytic = fields.Char()


    quantity = fields.Float()
    uom = fields.Char()

    price = fields.Float()

    taxes = fields.Char()
    discount = fields.Float()
    analytic_distribution = fields.Char()

    amount = fields.Float()
    location = fields.Char()
    location_dest = fields.Char()

    date = fields.Char()
    date_deadline = fields.Char()

    packaging = fields.Char()

    unit_cost = fields.Float()

    is_changed_location = fields.Boolean()
    is_changed_location_dest = fields.Boolean()

    is_changed_date = fields.Boolean()
    is_changed_date_deadline = fields.Boolean()

    is_changed_packaging = fields.Boolean()

    is_changed_unit_cost = fields.Boolean()
    is_changed_quantity = fields.Boolean()
    is_changed_price = fields.Boolean()
    is_changed_amount = fields.Boolean()
    is_changed_product = fields.Boolean()
    is_changed_account = fields.Boolean()
    is_changed_analytic = fields.Boolean()
    is_changed_uom = fields.Boolean()
    is_changed_taxes = fields.Boolean()
    is_changed_discount = fields.Boolean()
    is_changed_analytic_distribution = fields.Boolean()



    partner = fields.Char()
    label = fields.Char()

    debit = fields.Float()
    credit = fields.Float()

    is_changed_partner = fields.Boolean()
    is_changed_label = fields.Boolean()

    is_changed_debit = fields.Boolean()
    is_changed_credit = fields.Boolean()