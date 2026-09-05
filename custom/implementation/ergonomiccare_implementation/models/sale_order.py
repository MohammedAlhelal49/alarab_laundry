from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    patient_id = fields.Many2one(
        'res.partner',
        string='Patient Name',
        domain="[('is_company', '=', False)]",
    )
    patient_code = fields.Char(string='Code' ,default='E001')
    manufacturer = fields.Char(string='Manufacturer')

    mrn = fields.Char(
        string='MR No.',
        related='patient_id.mrn',
        readonly=False
    )

    claim_number = fields.Char(
        string='Claim No.',
    )

    lpo_authorization_type = fields.Selection(
        selection=[
            ('lpo', 'LPO Number'),
            ('authorization', 'Authorization Number'),
        ],
        string='LPO / Authorization No.',
        tracking=True
    )

    lpo_number = fields.Char(string="LPO Number")

    authorization_number = fields.Char(
        string="Authorization Number",
    )

    def _prepare_picking_vals(self):
        vals = super()._prepare_picking_vals()

        vals.update({
            'lpo_authorization_type': self.lpo_authorization_type,
            'lpo_number': self.lpo_number,
            'authorization_number': self.authorization_number,
        })

        return vals


    theqa_no = fields.Char(string='Card No.', related='patient_id.theqa_no', readonly=False)
    product_ids = fields.Many2many(
        'product.product',
        'crm_lead_product_rel',
        'lead_id',
        'product_id',
        string='Product',
        related='patient_id.product_ids',
        readonly=False
    )
    product_description = fields.Text(string="Product Description", related='patient_id.product_description', readonly=False)

    warranty_value = fields.Integer(string='Warranty', default=1)
    warranty_unit = fields.Selection(
        [('month', 'Months'), ('year', 'Years')],
        string='Warranty Unit',
        default='year'
    )

    # Delivery Duration fields
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

    @api.depends('delivery_duration_from', 'delivery_duration_to', 'delivery_duration_unit')
    def _compute_delivery_duration_display(self):
        for rec in self:
            if rec.delivery_duration_from and rec.delivery_duration_to and rec.delivery_duration_unit:
                unit = dict(self._fields['delivery_duration_unit'].selection).get(rec.delivery_duration_unit, '')
                rec.delivery_duration_display = f"{rec.delivery_duration_from} to {rec.delivery_duration_to} {unit.lower()}"
            else:
                rec.delivery_duration_display = ""


    def _prepare_invoice(self):
        self.ensure_one()
        vals = super()._prepare_invoice()

        medical_fields = {
            'patient_id': self.patient_id.id,
            'claim_number': self.claim_number,
            'lpo_authorization_type': self.lpo_authorization_type,
            'lpo_number': self.lpo_number,
            'authorization_number': self.authorization_number,

        }

        vals.update(medical_fields)
        return vals
