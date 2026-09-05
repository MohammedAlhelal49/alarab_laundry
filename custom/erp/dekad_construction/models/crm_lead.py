from email.policy import default

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ConstructionLeadRequirement(models.Model):
    _name = "construction.lead.requirement"
    _description = "Lead Requirement (maps to JCS later)"
    _order = "sequence, id"

    lead_id = fields.Many2one('crm.lead', string="Lead", ondelete='cascade', index=True, required=True)
    sequence = fields.Integer(string="Step #")
    product_id = fields.Many2one('product.product')
    note = fields.Text(string="Notes / Requirement Details")
    quantity = fields.Float(string="Quantity", default=1.0)
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    active = fields.Boolean(default=True)

    @api.onchange('lead_id')
    def _onchange_lead_id_set_sequence(self):
        if not self.sequence and self.lead_id:
            existing = self.lead_id.requirement_ids.filtered(
                lambda r: r.id != self.id
            )
            self.sequence = (max(existing.mapped('sequence')) if existing else 0) + 1

    @api.onchange('product_id')
    def _onchange_product_assign_sequence(self):
        if not self.sequence and self.lead_id:
            existing = self.lead_id.requirement_ids.filtered(
                lambda r: r.id != self.id
            )
            self.sequence = (max(existing.mapped('sequence')) if existing else 0) + 1

    # -----------------------------------------
    # Auto-fill from product
    # -----------------------------------------

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                if rec.product_id.uom_id:
                    rec.uom_id = rec.product_id.uom_id.id


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    date_deadline = fields.Date(required=False)

    project_type = fields.Selection([
        ('in_house', 'In-House'),
        ('client_contract', 'Client Contract')
    ], string="Project Type", required=True, default='client_contract')

    requirement_ids = fields.One2many(
        'construction.lead.requirement', 'lead_id',
        string="Client Requirements (Standard Steps)",
        copy=True
    )

    requirement_state = fields.Selection([
        ('draft', 'Draft'),
        ('requirements_confirmed', 'Requirements Confirmed'),
    ], default='draft')

    construction_responsible_id = fields.Many2one(
        'hr.employee',
        required=True,
        string="Construction Responsible",
        help="The user actively responsible for the construction project, distinct from the salesperson.",
        default=lambda self: self.env.user.employee_id
    )

    construction_deadline = fields.Date(
        required=True,
        string="Construction Deadline",
        help="Target deadline specifically for the construction project."
    )

    job_cost_project_id = fields.Many2one(
        'job.cost.project',
        string="Job Cost Project",
        readonly=True
    )

    job_cost_project_count = fields.Integer(
        string="Job Cost Project Count",
        compute="_compute_job_cost_project_count",
    )

    def _compute_job_cost_project_count(self):
        for lead in self:
            lead.job_cost_project_count = self.env["job.cost.project"].search_count([
                ("lead_id", "=", lead.id)
            ])

    project_id = fields.Many2one(
        'project.project',
        string="Related Project",
        readonly=True,
        help="The project automatically created when this lead is won."
    )

    @api.model
    def create(self, vals):
        lead = super().create(vals)

        # Log the action using construction.log model
        self.env['construction.log'].create_log(
            description=f"Lead '{lead.name}' was created.",
            model_name='crm.lead',
            record=lead,
            log_type='action',
        )

        return lead

    def unlink(self):
        """Intercept deletion requests and block them if construction requirements are present."""
        for lead in self:
            if lead.requirement_ids:
                raise UserError(_(
                    "You cannot delete the lead '%s' because it contains active client requirements. "
                    "Please clear the client requirements table or archive this record instead."
                ) % lead.name)

        # Safe fallback to execute standard core engine deletion if empty
        return super(CRMLead, self).unlink()

    def action_create_job_cost_project(self):
        """Build a Job Cost Project from the lead requirements and generate job cost sheets."""
        self = self.with_context(bypass_costing_check=True)

        for lead in self:
            # 1) Prevent duplicate packages
            if lead.job_cost_project_id:
                raise UserError(_("A job cost project has already been created for this lead."))

            if not lead.requirement_ids:
                raise UserError(_("No requirements found on this lead."))

            # 2) Create package using the new Construction Deadline
            package = self.env['job.cost.project'].create({
                'name': f"Job Cost Project for {lead.name}",
                'lead_id': lead.id,
                'employee_id': lead.construction_responsible_id.id if lead.construction_responsible_id else False,
                'partner_id': lead.partner_id.id,
                'lead_deadline': lead.construction_deadline,
                'project_type': lead.project_type,
            })

            # 3) Create job cost sheets for each requirement
            jcs_env = self.env['job.cost.sheet']
            jcs_list = []
            seq = 1

            for req in lead.requirement_ids:
                if not req.product_id:
                    raise UserError(_("Each requirement must have a service selected."))

                jcs = jcs_env.create({
                    'name': req.product_id.name,
                    'sequence': seq,
                    'job_cost_project_id': package.id,
                    'employee_id': lead.construction_responsible_id.id if lead.construction_responsible_id else False,
                    'partner_id': lead.partner_id.id,
                    'requirement_note': req.note,
                    'quantity': req.quantity,
                    'uom_id': req.uom_id.id if req.uom_id else False,
                    'lead_deadline': lead.construction_deadline,
                })
                jcs_list.append(jcs.id)
                seq += 1

            # 4) Link package → lead
            lead.job_cost_project_id = package.id

            # 5) Make requirements read-only
            lead.requirement_state = 'requirements_confirmed'

            # 6) Chatter log
            lead.message_post(body=_(
                "✔ A job cost project has been created with %s client requirements."
            ) % len(jcs_list))

            # 7) Log the action using construction.log model
            self.env['construction.log'].create_log(
                description=f"Job cost project for {lead.name} has been created with {len(jcs_list)} job cost sheets.",
                model_name='job.cost.project',
                record=self,
                log_type='action',
            )

        return True

    def action_open_related_job_cost_project(self):
        """Open the linked job cost project in form view."""
        self.ensure_one()
        if not self.job_cost_project_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': 'Job Cost Project',
            'res_model': 'job.cost.project',
            'view_mode': 'form',
            'res_id': self.job_cost_project_id.id,
            'target': 'current',
        }
