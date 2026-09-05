from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.tools import format_date
from odoo.exceptions import UserError




class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pro_id = fields.Many2one(
        'hr.employee',
        'PRO',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
    )
    labor_card_number = fields.Char(string="Labor Card No.")
    last_working_date = fields.Date(string="Last Working Date")
    cancellation_date = fields.Date(string="Cancellation Date")

    id_expiry_reminders_sent = fields.Char(default="")
    visa_expiry_reminders_sent = fields.Char(default="")
    passport_expiry_reminders_sent = fields.Char(default="")
    work_permit_expiry_reminders_sent = fields.Char(default="")
    visa_attachment_ids = fields.Many2many(
        "ir.attachment",
        "employee_visa_ir_attachments_rel",
        "employee_id",
        "attachment_id",
        string="Visa Attachments",
        copy=False,
    )
    employment_status = fields.Selection(
        [
            ("active", "Active"),
            ("probation", "Probation"),
            ("resigned", "Resigned"),
            ("terminated", "Terminated"),
        ],
        string="Employment Status",
        tracking=True,
    )
    employment_type = fields.Selection(
        [
            ("permanent", "Permanent"),
            ("contract", "Contract"),
            ("temporary", "Temporary"),
            ("intern", "Intern"),
        ],
        string="Employment Type",
        tracking=True,
    )
    insurance_number = fields.Char(string="Insurance Number")

    insurance_expiry_date = fields.Date(
        string="Insurance Expiry Date"
    )

    insurance_attachment_ids = fields.Many2many(
        "ir.attachment",
        "employee_insurance_ir_attachments_rel",
        "employee_id",
        "attachment_id",
        string="Insurance Attachments",
        copy=False,
    )

    insurance_reminders_sent = fields.Char(default="")


    def _get_responsible_users(self, emp):
        users = self.env['res.users']

        for field in ['parent_id', 'coach_id', 'pro_id']:
            employee = getattr(emp, field, False)
            if employee and employee.user_id:
                users |= employee.user_id

        # fallback
        if not users:
            users = self.env.user

        return users

    def _send_expiry_email(self, emp, users, template, doc_type, expiry_date):
        if not template:
            return

        emails = [user.email for user in users if user.email]

        if not emails:
            return

        template.with_context(
            doc_type=doc_type,
            expiry_date=expiry_date
        ).send_mail(
            emp.id,
            email_values={
                'email_to': ','.join(emails)
            },
            force_send=True
        )

    @api.model
    def _cron_check_document_expiry(self):
        # Get configurable reminder days (e.g. 30,7,3)
        days_string = self.env["ir.config_parameter"].sudo().get_param(
            "hr.document_expiry_days",
            default="30,7,3",
        )

        reminder_days = sorted({
            int(day.strip())
            for day in days_string.split(",")
            if day.strip().isdigit() and int(day.strip()) >= 0
        })

        today = fields.Date.today()

        # Activity type
        activity_type = self.env.ref(
            "dekad_hr_enhancement.mail_activity_document_expired",
            raise_if_not_found=False,
        )

        if not activity_type:
            return

        # Email template
        template_id = self.env["ir.config_parameter"].sudo().get_param(
            "hr.document_expiry_template_id"
        )

        template = self.env.ref(
            "dekad_hr_enhancement.mail_template_document_expiry",
            raise_if_not_found=False,
        )

        if template_id:
            try:
                template = self.env["mail.template"].browse(int(template_id))
            except (TypeError, ValueError):
                pass

        employees = self.search([
            "|", "|", "|",
            ("id_expiry_date", "!=", False),
            ("visa_expire", "!=", False),
            ("passport_expiry_date", "!=", False),
            ("work_permit_expiration_date", "!=", False),
            ("insurance_expiry_date", "!=", False)
        ])

        documents = [
            {
                "field": "id_expiry_date",
                "sent_field": "id_expiry_reminders_sent",
                "summary": "ID Expiry",
                "doc_type": "ID",
                "number": "identification_id",
                "label": "ID",
            },
            {
                "field": "visa_expire",
                "sent_field": "visa_expiry_reminders_sent",
                "summary": "Visa Expiry",
                "doc_type": "Visa",
                "number": False,
                "label": "Visa",
            },
            {
                "field": "passport_expiry_date",
                "sent_field": "passport_expiry_reminders_sent",
                "summary": "Passport Expiry",
                "doc_type": "Passport",
                "number": "passport_id",
                "label": "Passport",
            },
            {
                "field": "work_permit_expiration_date",
                "sent_field": "work_permit_expiry_reminders_sent",
                "summary": "Work Permit Expiry",
                "doc_type": "Work Permit",
                "number": "permit_no",
                "label": "Work Permit",
            },
            {
                "field": "insurance_expiry_date",
                "sent_field": "insurance_reminders_sent",
                "summary": "Insurance Expiry",
                "doc_type": "Insurance",
                "number": "insurance_number",
                "label": "Insurance",
            },
        ]

        for emp in employees:
            users = self._get_responsible_users(emp)

            vals = {}

            for doc in documents:
                expiry_date = getattr(emp, doc["field"])

                if not expiry_date:
                    continue

                days_left = (expiry_date - today).days

                if days_left < 0:
                    continue

                if days_left not in reminder_days:
                    continue

                sent = getattr(emp, doc["sent_field"]) or ""

                sent_days = {
                    int(day)
                    for day in sent.split(",")
                    if day.strip().isdigit()
                }

                if days_left in sent_days:
                    continue

                if doc["number"]:
                    note = _(
                        "%(label)s %(number)s for %(employee)s expires on %(date)s",
                        label=doc["label"],
                        number=getattr(emp, doc["number"]) or "",
                        employee=emp.name,
                        date=format_date(self.env, expiry_date),
                    )
                else:
                    note = _(
                        "%(label)s for %(employee)s expires on %(date)s",
                        label=doc["label"],
                        employee=emp.name,
                        date=format_date(self.env, expiry_date),
                    )

                for user in users:
                    emp.activity_schedule(
                        activity_type_id=activity_type.id,
                        summary=doc["summary"],
                        note=note,
                        user_id=user.id,
                        date_deadline=expiry_date,
                    )

                self._send_expiry_email(
                    emp,
                    users,
                    template,
                    doc_type=doc["doc_type"],
                    expiry_date=expiry_date,
                )

                sent_days.add(days_left)

                vals[doc["sent_field"]] = ",".join(
                    str(day) for day in sorted(sent_days, reverse=True)
                )

            if vals:
                emp.write(vals)


    def action_open_my_profile(self):
        employee = self.search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            raise UserError(_("No employee record is linked to your user account."))
        view = self.env['ir.ui.view'].search(
            [('name', '=', 'hr.employee.profile.form')], limit=1
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Profile',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': employee.id,
            'views': [(view.id if view else False, 'form')],
            'target': 'current',
        }

    def write(self, vals):
        if "id_expiry_date" in vals:
            vals["id_expiry_reminders_sent"] = ""

        if "visa_expire" in vals:
            vals["visa_expiry_reminders_sent"] = ""

        if "passport_expiry_date" in vals:
            vals["passport_expiry_reminders_sent"] = ""

        if "work_permit_expiration_date" in vals:
            vals["work_permit_expiry_reminders_sent"] = ""

        if "insurance_expiry_date" in vals:
            vals["insurance_reminders_sent"] = ""

        return super().write(vals)

    @api.model
    def _cron_check_work_permit_validity(self):
        """Disabled: handled by _cron_check_document_expiry."""
        return