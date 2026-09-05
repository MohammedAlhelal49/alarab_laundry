from odoo import fields, models, api

class DekadBackupLog(models.Model):
    _name = "dekad.backup.log"
    _description = "Database Backup Log"
    _order = "started_at desc"

    name = fields.Char(string="Name", required=True, copy=False, readonly=True, default="New")
    db_name = fields.Char(string="Database Name", readonly=True)
    state = fields.Selection(
        [("success", "Success"), ("failed", "Failed")],
        string="Status",
        readonly=True,
        default="success",
    )
    trigger = fields.Selection(
        [("manual", "Manual"), ("cron", "Scheduled")],
        string="Trigger",
        readonly=True,
        default="manual",
    )
    file_path = fields.Char(string="File Path", readonly=True)
    file_size_mb = fields.Float(string="Size (MB)", readonly=True)
    started_at = fields.Datetime(string="Started At", readonly=True)
    finished_at = fields.Datetime(string="Finished At", readonly=True)
    duration_seconds = fields.Float(string="Duration (s)", readonly=True)
    message = fields.Text(string="Message/Error", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("dekad.backup.log") or "New"
        return super().create(vals_list)

    def action_download(self):
        """Return URL to download the backup file via the controller."""
        self.ensure_one()
        if not self.file_path or not self.state == "success":
            return False
        return {
            "type": "ir.actions.act_url",
            "url": f"/dekad/backup/download/{self.id}",
            "target": "new",
        }
