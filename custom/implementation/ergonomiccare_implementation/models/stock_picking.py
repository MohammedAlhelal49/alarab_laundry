from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    patient_id = fields.Many2one(
        'res.partner',
        string='Patient Name',
        domain="[('is_company', '=', False)]",
        compute="_compute_patient_id",
        store=True,
        readonly=False,
    )
    patient_code = fields.Char(string='Code', default='E001')
    manufacturer = fields.Char(string='Manufacturer')

    mrn = fields.Char(
        string='MR No.',
        related='patient_id.mrn',
        readonly=False
    )
    claim_number = fields.Char(
        string="Claim No.",
        related="sale_id.claim_number",
        store=True,
        readonly=True,
    )

    theqa_no = fields.Char(string='Card No.', related='patient_id.theqa_no', readonly=False)
    warranty_value = fields.Integer(string='Warranty', default=1)
    warranty_unit = fields.Selection(
        [('month', 'Months'), ('year', 'Years')],
        string='Warranty Unit',
        default='year'
    )
    lpo_authorization_type = fields.Selection(
        related='sale_id.lpo_authorization_type',
        store=True,
        readonly=True
    )
    delivery_duration_from = fields.Integer(string='Delivery Duration From')
    delivery_duration_to = fields.Integer(string='To')
    delivery_duration_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months')
    ], string='Duration Unit', default='week')

    delivery_duration_display = fields.Char(
        string='Delivery Duration Display',
        compute='_compute_delivery_duration_display',
        store=True
    )

    product_ids = fields.Many2many(
        'product.product',
        'crm_lead_product_rel',
        'lead_id',
        'product_id',
        string='Product',
        related='patient_id.product_ids',
        readonly=False
    )
    product_description = fields.Text(string="Product Description", related='patient_id.product_description',
                                      readonly=False)


    attachment_ids = fields.Many2many(
        'ir.attachment',
        'stock_picking_ir_attachments_rel',
        'picking_id',
        'attachment_id',
        string='Attachments'
    )

    lpo_number = fields.Char(
        string="LPO Number",
        related="sale_id.lpo_number",
        store=True,
        readonly=False
    )

    authorization_number = fields.Char(
        string="Authorization Number",
        related="sale_id.authorization_number",
        store=True,
        readonly=False
    )

    # Override validation button
    def button_validate(self):
        for picking in self:
            # Only for Delivery Orders
            if picking.picking_type_code == 'outgoing':
                if not picking.attachment_ids:
                    raise UserError(
                        _("Please upload at least one attachment before validating the Delivery Note.")
                    )

            signed_pdf = self.env['ir.attachment'].search([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
                ('name', 'ilike', '_signed_delivery_slip'),
            ], limit=1)

            if not signed_pdf:
                raise UserError(
                    _("Signature is required before validation.")
                )

        return super().button_validate()


    @api.depends('delivery_duration_from', 'delivery_duration_to', 'delivery_duration_unit')
    def _compute_delivery_duration_display(self):
        for rec in self:
            if rec.delivery_duration_from and rec.delivery_duration_to and rec.delivery_duration_unit:
                unit = dict(self._fields['delivery_duration_unit'].selection).get(rec.delivery_duration_unit, '')
                rec.delivery_duration_display = f"{rec.delivery_duration_from} to {rec.delivery_duration_to} {unit.lower()}"
            else:
                rec.delivery_duration_display = ""

    @api.depends('sale_id.patient_id')
    def _compute_patient_id(self):
        for picking in self:
            picking.patient_id = picking.sale_id.patient_id


    @api.depends('sale_id.authorization_number')
    def _compute_authorization_number(self):
        for picking in self:
            if picking.sale_id:
                picking.authorization_number = picking.sale_id.authorization_number
            else:
                picking.authorization_number = False