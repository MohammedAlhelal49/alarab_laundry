from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gmr_default_vendor_id = fields.Many2one(
        'res.partner',
        string='Default Vendor',
        config_parameter='dekad_material_request.default_vendor_id',
        domain="[('supplier_rank', '>', 0)]",
        groups='dekad_material_request.group_gmr_admin',
        help='Default vendor when creating purchase orders from material requests'
    )

    gmr_default_approver_id = fields.Many2one(
        'res.users',
        string='Default Approver',
        config_parameter='dekad_material_request.default_approver_id',
        groups='dekad_material_request.group_gmr_admin',
        help='Pre-filled as the Approver on new material requests. The '
             'requester can still change it before submitting.'
    )

    gmr_doc_type_policy = fields.Selection([
        ('po_only', 'Purchase Order Only'),
        ('bill_only', 'Vendor Bill Only'),
        ('both', 'Both (let Admin choose each time)'),
    ], string='Document Type Policy',
        config_parameter='dekad_material_request.doc_type_policy',
        default='both',
        groups='dekad_material_request.group_gmr_admin',
        help='Restricts what an Admin can create from the "Create PO/Bill" '
             'wizard. If restricted to one type, the choice is hidden from '
             'the wizard entirely (no way to pick the other type).')

    gmr_default_doc_type = fields.Selection([
        ('po', 'Purchase Order'),
        ('bill', 'Vendor Bill'),
    ], string='Default Choice (when both are allowed)',
        config_parameter='dekad_material_request.default_doc_type',
        default='po',
        groups='dekad_material_request.group_gmr_admin',
        help='Which option is pre-selected in the wizard when the policy '
             'above is set to "Both". Ignored otherwise.')