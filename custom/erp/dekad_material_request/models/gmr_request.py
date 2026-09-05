from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class GmrRequest(models.Model):
    _name = 'gmr.request'
    _description = 'General Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # ==================== Basic Fields ====================
    name = fields.Char(
        string='Request Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    required_date = fields.Date(
        string='Required Date',
        tracking=True
    )

    # ==================== Project / Department ====================
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Project / Department',
        tracking=True,
        help='Select the analytic account (project or department) for this request'
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True,
        domain="[('account_id', '=', analytic_account_id)]",
        help='Project this request belongs to. Determines which tasks '
             'are selectable on the request lines below. Required only '
             'if the selected Analytic Account has at least one linked '
             'project; optional for analytic accounts with no project '
             '(e.g. a purely administrative department).'
    )

    has_linked_projects = fields.Boolean(
        string='Has Linked Projects',
        compute='_compute_has_linked_projects',
        help='Technical field: whether the selected Analytic Account has '
             'at least one project.project linked to it. Drives whether '
             'Project is required on this request.'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]",
        groups='dekad_material_request.group_gmr_admin',
        tracking=True,
        default=lambda self: self._default_vendor_id(),
        help='Default vendor for this request. Only visible/editable by '
             'Admins. Pre-fills the Vendor field on the PO/Bill creation '
             'wizard, and fills in any request line that doesn\'t have '
             'its own vendor set yet.'
    )

    @api.model
    def _default_vendor_id(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'dekad_material_request.default_vendor_id'
        )
        if param and str(param).isdigit():
            vendor = self.env['res.partner'].browse(int(param)).exists()
            if vendor:
                return vendor.id
        return False

    # ==================== Users ====================
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True,
        tracking=True,
        default=lambda self: self._default_approver_id(),
        help='User responsible for approving this request'
    )

    @api.model
    def _default_approver_id(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'dekad_material_request.default_approver_id'
        )
        if param and str(param).isdigit():
            user = self.env['res.users'].browse(int(param)).exists()
            if user:
                return user.id
        return False

    # ==================== Display Names (stored, no res.users read needed) ====================
    requested_by_name = fields.Char(
        string='Requested By',
        compute='_compute_user_names',
        store=True
    )

    approver_name = fields.Char(
        string='Approver Name',
        compute='_compute_user_names',
        store=True
    )

    # ==================== Timestamps ====================
    submit_date = fields.Datetime(string='Submit Date', readonly=True)
    approval_date = fields.Datetime(string='Approval Date', readonly=True)

    # ==================== Approval Info ====================
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_by_name = fields.Char(
        string='Approved By',
        compute='_compute_user_names',
        store=True
    )
    approval_comment = fields.Text(string='Approval Comment')

    # ==================== Cancellation Info ====================
    cancel_date = fields.Datetime(string='Cancel Date', readonly=True)
    cancelled_by = fields.Many2one('res.users', string='Cancelled By', readonly=True)
    cancelled_by_name = fields.Char(
        string='Cancelled By',
        compute='_compute_user_names',
        store=True
    )

    # ==================== State ====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('po_created', 'PO Created'),
        ('bill_created', 'Bill Created'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True, copy=False)

    # ==================== Lines ====================
    request_line_ids = fields.One2many(
        'gmr.request.line',
        'request_id',
        string='Request Lines'
    )

    # ==================== Description ====================
    description = fields.Text(string='Description')

    # ==================== Purchase Order Link ====================
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'gmr_request_purchase_order_rel',
        'request_id',
        'order_id',
        string='Purchase Orders',
        readonly=True,
        copy=False
    )

    # ==================== Vendor Bill Link ====================
    account_move_ids = fields.Many2many(
        'account.move',
        'gmr_request_account_move_rel',
        'request_id',
        'move_id',
        string='Vendor Bills',
        readonly=True,
        copy=False
    )

    # ==================== Computed Fields ====================
    purchase_order_count = fields.Integer(
        string='PO Count',
        compute='_compute_purchase_order_count'
    )

    account_move_count = fields.Integer(
        string='Bill Count',
        compute='_compute_account_move_count'
    )

    line_count = fields.Integer(
        string='Line Count',
        compute='_compute_line_count'
    )

    total_qty = fields.Float(
        string='Total Requested Qty',
        compute='_compute_total_qty'
    )

    total_approved_qty = fields.Float(
        string='Total Approved Qty',
        compute='_compute_total_approved_qty'
    )

    @api.depends('request_line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.request_line_ids)

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = len(record.purchase_order_ids)

    @api.depends('account_move_ids')
    def _compute_account_move_count(self):
        for record in self:
            record.account_move_count = len(record.account_move_ids)

    @api.depends('request_line_ids.qty')
    def _compute_total_qty(self):
        for record in self:
            record.total_qty = sum(record.request_line_ids.mapped('qty'))

    @api.depends('request_line_ids.approved_qty')
    def _compute_total_approved_qty(self):
        for record in self:
            record.total_approved_qty = sum(record.request_line_ids.mapped('approved_qty'))

    @api.depends('requested_by', 'approver_id', 'approved_by', 'cancelled_by')
    def _compute_user_names(self):
        for rec in self:
            rec.requested_by_name = rec.sudo().requested_by.name or ''
            rec.approver_name = rec.sudo().approver_id.name or ''
            rec.approved_by_name = rec.sudo().approved_by.name or ''
            rec.cancelled_by_name = rec.sudo().cancelled_by.name or ''

    @api.depends('analytic_account_id')
    def _compute_has_linked_projects(self):
        for record in self:
            record.has_linked_projects = bool(record.analytic_account_id) and bool(
                self.env['project.project'].search_count(
                    [('account_id', '=', record.analytic_account_id.id)], limit=1
                )
            )

    @api.constrains('analytic_account_id', 'project_id')
    def _check_project_required(self):
        for record in self:
            if record.has_linked_projects and not record.project_id:
                raise ValidationError(_(
                    'The Analytic Account "%s" has one or more linked projects. '
                    'Please select one in the Project field.'
                ) % record.analytic_account_id.display_name)

    @api.constrains('project_id', 'request_line_ids.task_id')
    def _check_line_tasks_required(self):
        for record in self:
            if record.project_id:
                missing = record.request_line_ids.filtered(lambda l: l.product_id and not l.task_id)
                if missing:
                    raise ValidationError(_(
                        'This request has a Project set, so every line needs a '
                        'Task. Missing on: %s'
                    ) % ', '.join(missing.mapped('product_id.display_name')))

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id(self):
        """Project is filtered to those linked to the selected Analytic
        Account (project.project.account_id). Clear it if it no longer
        matches after the account changes, so we never keep a
        Project/Analytic Account combination that doesn't actually
        correspond to each other."""
        if self.project_id and self.project_id.account_id != self.analytic_account_id:
            self.project_id = False

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Force the header Vendor onto every line immediately in the
        UI. The request's Vendor is the single source of truth -- any
        change here always overwrites all lines, matching the write()
        override below which enforces the same rule on save."""
        for line in self.request_line_ids:
            line.vendor_id = self.vendor_id

    # ==================== CRUD ====================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gmr.request') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'vendor_id' in vals:
            for record in self:
                if record.request_line_ids:
                    record.sudo().request_line_ids.write({'vendor_id': vals['vendor_id']})
        return res

    # ==================== User Actions ====================

    def action_submit(self):
        """User submits request for approval."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            if not record.request_line_ids:
                raise UserError(_('Please add at least one request line.'))

            record.with_context(
                mail_notrack=True,
                tracking_disable=True,
            ).write({
                'state': 'pending_approval',
                'submit_date': fields.Datetime.now(),
            })

            # Pre-fill Approved Qty with the Requested Qty so the approver
            # only needs to adjust the lines they actually want to change.
            for line in record.request_line_ids:
                line.approved_qty = line.qty

            # Notify the selected approver
            # Skip only if approver is the same user submitting the request
            if record.approver_id and record.approver_id != self.env.user:
                try:
                    record.with_context(
                        mail_notify_force_send=False,
                        mail_auto_subscribe_no_notify=True,
                        tracking_disable=True,
                    ).activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=record.approver_id.id,
                        summary=_('Material Request - Approval Required'),
                        note=_('New material request %s needs your approval.') % record.name
                    )
                except Exception:
                    pass

            record.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                body=_('Request submitted by %s.') % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    # ==================== Approver Actions ====================

    def action_approve(self):
        """Approver or Admin approves the request."""
        for record in self:
            if record.state != 'pending_approval':
                raise UserError(_('Only pending requests can be approved.'))

            # Mark activity as done
            activities = record.activity_ids.filtered(
                lambda a: a.user_id == self.env.user
            )
            if activities:
                try:
                    activities.with_context(
                        mail_notify_force_send=False,
                        tracking_disable=True,
                    ).action_feedback(feedback=_('Approved'))
                except Exception:
                    activities.unlink()

            record.with_context(
                mail_notrack=True,
                tracking_disable=True,
            ).write({
                'state': 'approved',
                'approval_date': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })

            record.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                body=_('Request approved by %s.') % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

            # Notify all Admin users that request is ready for procurement
            admin_group = self.env.ref('dekad_material_request.group_gmr_admin', raise_if_not_found=False)
            if admin_group:
                admin_users = admin_group.users.filtered(lambda u: u.active and u.id != self.env.user.id)
                for admin in admin_users:
                    try:
                        record.with_context(
                            mail_notify_force_send=False,
                            mail_auto_subscribe_no_notify=True,
                            tracking_disable=True,
                        ).activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=admin.id,
                            summary=_('Material Request Ready for Procurement'),
                            note=_('Request %s has been approved by %s and is ready for PO/Bill creation.') % (
                                record.name, self.env.user.name
                            )
                        )
                    except Exception:
                        pass

    def action_reject(self):
        """Approver or Admin rejects the request."""
        for record in self:
            if record.state != 'pending_approval':
                raise UserError(_('Only pending requests can be rejected.'))

            # Mark activity as done
            activities = record.activity_ids.filtered(
                lambda a: a.user_id == self.env.user
            )
            if activities:
                try:
                    activities.with_context(
                        mail_notify_force_send=False,
                        tracking_disable=True,
                    ).action_feedback(feedback=_('Rejected'))
                except Exception:
                    activities.unlink()

            record.with_context(
                mail_notrack=True,
                tracking_disable=True,
            ).write({
                'state': 'rejected',
                'approval_date': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })

            record.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                body=_('Request rejected by %s.') % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    # ==================== Admin Actions ====================

    def action_reset_to_draft(self):
        """Reset request back to Draft.

        - The requester (owner) may reset from 'pending_approval'
          (before the approver has decided) or 'rejected' (to fix and
          resubmit after a rejection).
        - Admins may reset only from 'rejected'. Once a request is
          'approved', it can no longer be reset to draft by anyone --
          the approval decision is final at that point.
        """
        is_admin = self.env.user.has_group('dekad_material_request.group_gmr_admin')
        for record in self:
            if record.state in ('po_created', 'bill_created', 'done'):
                raise UserError(_('Cannot reset to draft after PO or Bill is created.'))

            is_owner = record.requested_by == self.env.user
            if is_admin:
                allowed_states = ('rejected',)
            elif is_owner:
                allowed_states = ('pending_approval', 'rejected')
            else:
                allowed_states = ()

            if record.state not in allowed_states:
                raise UserError(_(
                    'You are not allowed to reset request %s to draft in its current state.'
                ) % record.name)

            # Clear any pending approval activities tied to this request
            record.activity_ids.unlink()

            record.with_context(
                mail_notrack=True,
                tracking_disable=True,
            ).write({
                'state': 'draft',
                'approval_date': False,
                'approved_by': False,
                'submit_date': False,
            })

            # Approved Qty becomes stale once back in draft; it will be
            # re-initialized from the (possibly edited) Requested Qty on
            # the next submit.
            record.request_line_ids.write({'approved_qty': 0.0})

            record.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                body=_('Request reset to draft by %s.') % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_cancel(self):
        """Cancel the request.

        - The requester (owner) may cancel only from 'draft' or
          'pending_approval' (before it has been approved).
        - Approvers/Admins may cancel from 'draft' or 'approved'.
          'pending_approval' is intentionally excluded for
          Approvers/Admins: while a request is pending, the only
          decisions available to them are Approve/Reject; cancelling
          is reserved for the owner at that stage.
        - Cancellation is never allowed once a PO/Bill has been created;
          that must be handled from the Purchase Order itself.
        """
        is_privileged = (
            self.env.user.has_group('dekad_material_request.group_gmr_approver')
            or self.env.user.has_group('dekad_material_request.group_gmr_admin')
        )
        for record in self:
            if record.state in ('po_created', 'bill_created', 'done'):
                raise UserError(_(
                    'Cannot cancel request %s after a PO or Bill has been created. '
                    'Please cancel the Purchase Order / Bill instead.'
                ) % record.name)

            is_owner = record.requested_by == self.env.user
            if is_privileged:
                allowed_states = ('draft', 'approved')
            elif is_owner:
                allowed_states = ('draft', 'pending_approval')
            else:
                allowed_states = ()

            if record.state not in allowed_states:
                raise UserError(_(
                    'You are not allowed to cancel request %s in its current state.'
                ) % record.name)

            # Clear any pending approval activities tied to this request
            record.activity_ids.unlink()

            record.with_context(
                mail_notrack=True,
                tracking_disable=True,
            ).write({
                'state': 'cancelled',
                'cancel_date': fields.Datetime.now(),
                'cancelled_by': self.env.user.id,
            })

            record.with_context(
                mail_notify_force_send=False,
                mail_auto_subscribe_no_notify=True,
            ).message_post(
                body=_('Request cancelled by %s.') % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_create_document(self):
        """Open wizard to create PO or Vendor Bill from approved requests."""
        already_processed = self.filtered(lambda r: r.state in ('po_created', 'bill_created', 'done'))
        if already_processed:
            raise UserError(_(
                'The following requests already have a document created:\n%s'
            ) % '\n'.join(already_processed.mapped('name')))

        not_approved = self.filtered(lambda r: r.state != 'approved')
        if not_approved:
            raise UserError(_(
                'The following requests are not approved:\n%s'
            ) % '\n'.join(not_approved.mapped('name')))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Purchase Document'),
            'res_model': 'gmr.create.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'gmr.request',
            }
        }

    # ==================== Smart Button Actions ====================

    def action_view_purchase_orders(self):
        """Smart button: view linked purchase orders."""
        self.ensure_one()
        if len(self.purchase_order_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Order'),
                'res_model': 'purchase.order',
                'res_id': self.purchase_order_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_add_products_wizard(self):
        """Create the Add Products wizard fully server-side (its lines
        get populated by GmrAddProductsWizard.create()) and open that
        existing record by res_id. Opening an existing id (read) is far
        more reliable than letting the client create+onchange a fresh
        'new' record with 100s of o2m sub-lines."""
        self.ensure_one()
        wizard = self.env['gmr.add.products.wizard'].create({
            'request_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Products'),
            'res_model': 'gmr.add.products.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_vendor_bills(self):
        """Smart button: view linked vendor bills."""
        self.ensure_one()
        if len(self.account_move_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Vendor Bill'),
                'res_model': 'account.move',
                'res_id': self.account_move_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bills'),
            'res_model': 'account.move',
            'domain': [('id', 'in', self.account_move_ids.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }