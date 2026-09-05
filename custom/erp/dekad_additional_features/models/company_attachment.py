import base64
from datetime import timedelta

from odoo import api, fields, models


class CompanyAttachment(models.Model):
    _name = "company.attachment"
    _description = "Company Attachment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date"

    name = fields.Char(
        required=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Attachment",
        readonly=True,
        copy=False,
    )

    upload_file = fields.Binary(
        string="Upload File",
        attachment=False,
    )

    upload_filename = fields.Char(
        string="Filename",
    )

    description = fields.Text()

    expiry_date = fields.Date(
        tracking=True,
    )

    notify_before = fields.Integer(
        string="Notify Before (Days)",
        default=30,
    )

    notification_type = fields.Selection(
        [
            ("email", "Email"),
            ("activity", "Activity"),
            ("both", "Both"),
        ],
        default="both",
        required=True,
    )

    user_ids = fields.Many2many(
        "res.users",
        string="Users",
    )

    group_ids = fields.Many2many(
        "res.groups",
        string="Security Groups",
    )

    status = fields.Selection(
        [
            ("valid", "Valid"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
        ],
        compute="_compute_status",
        store=True,
    )

    active = fields.Boolean(default=True)

    last_notification_date = fields.Date(
        copy=False,
        readonly=True,
    )

    @api.depends("expiry_date", "notify_before")
    def _compute_status(self):
        today = fields.Date.today()

        for rec in self:
            if not rec.expiry_date:
                rec.status = "valid"
                continue

            if rec.expiry_date < today:
                rec.status = "expired"
                continue

            notify_date = rec.expiry_date - timedelta(days=rec.notify_before)

            if today >= notify_date:
                rec.status = "expiring"
            else:
                rec.status = "valid"

    def _create_ir_attachment(self):
        """Create or update the linked ir.attachment."""
        for rec in self:
            if not rec.upload_file:
                continue

            values = {
                "name": rec.upload_filename or rec.name,
                "datas": rec.upload_file,
                "res_model": self._name,
                "res_id": rec.id,
                "mimetype": False,
            }

            if rec.attachment_id:
                rec.attachment_id.write(values)
            else:
                attachment = self.env["ir.attachment"].create(values)
                rec.attachment_id = attachment.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        records._create_ir_attachment()

        return records

    def write(self, vals):
        res = super().write(vals)

        if "upload_file" in vals or "upload_filename" in vals:
            self._create_ir_attachment()

        return res

    def unlink(self):
        attachments = self.mapped("attachment_id")
        res = super().unlink()
        attachments.unlink()
        return res

    def _get_notification_users(self):
        self.ensure_one()

        users = self.user_ids

        if self.group_ids:
            users |= self.group_ids.mapped("users")

        return users.filtered(lambda u: u.partner_id.email)

    @api.model
    def cron_check_attachment_expiry(self):
        today = fields.Date.today()

        template = self.env.ref(
            "dekad_additional_features.mail_template_company_attachment"
        )

        activity_type = self.env.ref(
            "mail.mail_activity_data_todo"
        )

        model_id = self.env["ir.model"]._get_id(self._name)

        records = self.search([
            ("active", "=", True),
            ("expiry_date", "!=", False),
        ])

        for rec in records:
            notify_date = rec.expiry_date - timedelta(days=rec.notify_before)

            if today < notify_date:
                continue

            if rec.last_notification_date == today:
                continue

            users = rec._get_notification_users()

            for user in users:

                if rec.notification_type in ("email", "both"):
                    template.send_mail(
                        rec.id,
                        force_send=True,
                        email_values={
                            "email_to": user.partner_id.email,
                        },
                    )

                if rec.notification_type in ("activity", "both"):
                    self.env["mail.activity"].create({
                        "activity_type_id": activity_type.id,
                        "summary": "Company Attachment Expiry",
                        "note": (
                            f'The attachment "{rec.name}" '
                            f'will expire on {rec.expiry_date}.'
                        ),
                        "user_id": user.id,
                        "res_model_id": model_id,
                        "res_id": rec.id,
                    })

            rec.last_notification_date = today