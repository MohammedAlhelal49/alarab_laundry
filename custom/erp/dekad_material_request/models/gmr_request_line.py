from odoo import models, fields, api


class GmrRequestLine(models.Model):
    _name = 'gmr.request.line'
    _description = 'General Material Request Line'

    # ==================== Relation ====================
    request_id = fields.Many2one(
        'gmr.request',
        string='Request Reference',
        required=True,
        ondelete='cascade'
    )

    # ==================== Product Info ====================
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )

    # ==================== Quantity ====================
    qty = fields.Float(
        string='Requested Qty',
        required=True,
        default=1.0,
        help='Quantity originally requested by the user. Editable only '
             'while the request is in Draft.'
    )

    approved_qty = fields.Float(
        string='Approved Qty',
        default=0.0,
        help='Quantity the Approver/Admin actually approves for this line. '
             'Pre-filled with the requested quantity when the request is '
             'submitted, and can be freely adjusted up or down by the '
             'Approver/Admin while the request is Pending Approval. This '
             'is the quantity used to generate the PO/Bill.'
    )

    # ==================== Task ====================
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='request_id.project_id',
        store=True,
        readonly=True,
        help='Technical field, mirrors the request\'s project. Used to '
             'restrict which tasks are selectable on this line.'
    )

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
        help='Task this line is related to. Only tasks belonging to the '
             'request\'s project are selectable. Required only if the '
             'request has a Project set; optional when the request runs '
             'against a project-less Analytic Account (e.g. a purely '
             'administrative department). Editable only while the '
             'request is in Draft.'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]",
        groups='dekad_material_request.group_gmr_admin',
        help='Preferred vendor for this specific line. Only visible/'
             'editable by Admins. Not required at the database level '
             '(regular users create lines without it); it is informational '
             'and pre-fills the PO/Bill wizard\'s Vendor field.'
    )

    # ==================== Additional Info ====================
    notes = fields.Text(string='Notes')

    # ==================== Related Fields ====================
    state = fields.Selection(
        related='request_id.state',
        string='Status',
        store=True
    )

    # ==================== Edit Permission (UI helper) ====================
    can_edit_approved_qty = fields.Boolean(
        string='Can Edit Approved Qty',
        compute='_compute_can_edit_approved_qty',
        help='Technical field controlling who may edit the Approved Qty '
             'column: only an Approver/Admin, and only while the request '
             'is Pending Approval.'
    )

    @api.depends('state')
    def _compute_can_edit_approved_qty(self):
        user = self.env.user
        is_admin = user.has_group('dekad_material_request.group_gmr_admin')
        is_approver = user.has_group('dekad_material_request.group_gmr_approver')
        for line in self:
            # Record rules already restrict which pending requests an
            # Approver/Admin can even see (assigned approver only), so
            # group membership is a sufficient check here.
            line.can_edit_approved_qty = line.state == 'pending_approval' and (is_admin or is_approver)

    # ==================== Purchase Line Link ====================
    purchase_line_ids = fields.Many2many(
        'purchase.order.line',
        'gmr_request_line_purchase_line_rel',
        'request_line_id',
        'purchase_line_id',
        string='PO Lines',
        readonly=True
    )

    # ==================== CRUD ====================
    @api.model_create_multi
    def create(self, vals_list):
        """Fall back to the parent request's default Vendor when a line
        is created without its own vendor_id. The request-level
        _onchange_vendor_id only fires when vendor_id itself changes, so
        it never reaches lines added afterward (e.g. via the Add
        Products wizard, which creates lines directly without going
        through that onchange). This is the single point that covers
        every creation path.

        vendor_id is a groups-restricted field (Admin only). Injecting
        it directly into the original vals would make create() raise
        AccessError whenever a non-admin user creates the line (e.g. a
        regular User adding products through the wizard) -- explicitly
        supplying a restricted field in vals is checked, unlike a plain
        field default. So: create first with the original vals, then
        apply the fallback via a sudo() follow-up write, which bypasses
        that check for this internal cascade only.
        """
        request_ids = {vals['request_id'] for vals in vals_list if vals.get('request_id')}
        vendors_by_request = {}
        if request_ids:
            for request in self.env['gmr.request'].sudo().browse(request_ids):
                vendors_by_request[request.id] = request.vendor_id.id

        records = super().create(vals_list)

        for vals, record in zip(vals_list, records):
            if not vals.get('vendor_id') and vals.get('request_id'):
                vendor_id = vendors_by_request.get(vals['request_id'])
                if vendor_id:
                    record.sudo().write({'vendor_id': vendor_id})
        return records

    # ==================== Onchange ====================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.notes:
            self.notes = self.product_id.description_purchase or ''
        # Immediate UI feedback when a line is added manually in the
        # list (before save); create() above covers it either way.
        if self.product_id and not self.vendor_id and self.request_id.vendor_id:
            self.vendor_id = self.request_id.vendor_id