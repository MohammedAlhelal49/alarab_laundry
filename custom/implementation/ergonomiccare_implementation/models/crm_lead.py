from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        domain="[('is_company', '=', False)]",
    )

    mrn = fields.Char(string='MR No.', related='patient_id.mrn', readonly=False)
    theqa_no = fields.Char(string='Card No.', related='patient_id.theqa_no', readonly=False)

    medical_report = fields.Selection([
        ('available', 'Available'),
        ('pending', 'Pending'),
        ('not_available', 'Not Available')
    ], string='Medical Report')

    medical_report_file = fields.Binary(string="Medical Report File", attachment=True)
    medical_report_file_name = fields.Char(string="Filename")
    product_line = fields.Selection(
        selection=[
            ("mobility", "Mobility"),
            ("prosthetics", "Prosthetics"),
            ("orthotics", "Orthotics"),
            ("medical_shoes", "Medical Shoes"),
        ],
        string="Product Line",
    )
    approval_no = fields.Char(
        string="Approval No."
    )

    approval_date = fields.Date(
        string="Approval Date"
    )

    authorization_expiry_date = fields.Date(
        string="Authorization Expiry Date"
    )

    order_date = fields.Date(
        string="Order Date"
    )

    expected_delivery_date = fields.Date(
        string="Expected Delivery Date"
    )

    product_ids = fields.Many2many(
        'product.product',
        'crm_lead_product_rel',
        'lead_id',
        'product_id',
        string='Product',
        related='patient_id.product_ids', readonly=False
    )
    product_description = fields.Text(string="Product Description", related='patient_id.product_description', readonly=False)


    consulting_clinical = fields.Selection([
        ('physiotherapist', 'Physiotherapist'),
        ('cpo', 'CPO'),
        ('clinical_consultant', 'Clinical Consultant'),
    ], string="Consulting Clinical")



    hospital_appointment = fields.Datetime(string="Hospital Appointment")
    casting_appointment = fields.Datetime(string="Casting Appointment")
    daman_approval = fields.Boolean(string="Daman’s Approval")

    measurement = fields.Boolean(string="Measurement")
    measurement_file = fields.Binary(string="", attachment=True)
    measurement_file_name = fields.Char(string="Filename")

    @api.constrains('measurement', 'measurement_file', 'measurement_file_name')
    def _check_measurement_file(self):
        for rec in self:
            if rec.measurement:
                if not rec.measurement_file:
                    raise ValidationError("You must upload a PDF file when Measurement is checked.")
                if rec.measurement_file_name and not rec.measurement_file_name.lower().endswith('.pdf'):
                    raise ValidationError("Only PDF files are allowed for Measurement.")

    @api.constrains('medical_report', 'medical_report_file', 'medical_report_file_name')
    def _check_medical_report_file(self):
        for rec in self:
            if rec.medical_report == 'available':
                if not rec.medical_report_file:
                    raise ValidationError("You must upload a PDF when Medical Report is 'Available'.")
                if rec.medical_report_file_name and not rec.medical_report_file_name.lower().endswith('.pdf'):
                    raise ValidationError("Only PDF files are allowed for Medical Report.")

    def _prepare_opportunity_quotation_context(self):
        """Extend context for sale.order creation to include patient_id"""
        self.ensure_one()

        # Call super to keep existing context values
        context = super()._prepare_opportunity_quotation_context()

        # Add patient_id to the context
        context.update({
            'default_patient_id': self.patient_id.id
        })

        return context


    def write(self, vals):
        if "stage_id" in vals:


            if self.env.user.can_move_locked_stage:
                return super().write(vals)

            new_stage = self.env["crm.stage"].browse(vals["stage_id"])


            locked_records = self.filtered(lambda r: r.stage_id.lock_stage)
            if locked_records:
                stage_names = ", ".join(locked_records.mapped("stage_id.name"))
                raise UserError(
                    f"You cannot move cards out of locked stage(s): {stage_names}"
                )


            if new_stage.lock_stage:
                raise UserError(
                    f"You cannot move cards into locked stage '{new_stage.name}'"
                )

        return super().write(vals)