# File: dekad_auto_database_backup/models/res_config_settings.py

from odoo import api, fields, models


class DekadBackupSettings(models.TransientModel):
    """Standalone wizard for CENTRALIZED backup settings."""

    _name = "dekad.backup.settings"
    _description = "Centralized Database Backup Settings"

    dekad_backup_enabled = fields.Boolean(string="Enable automatic database backup")
    dekad_backup_daily = fields.Boolean(string="Repeat backup every day")
    dekad_backup_time = fields.Char(string="First backup time (HH:MM)")
    dekad_backup_end_time = fields.Char(string="Last backup time (HH:MM)")
    dekad_backup_per_day = fields.Integer(string="Number of backups per day")
    dekad_backup_keep_count = fields.Integer(string="Number of backups to keep")
    dekad_backup_path = fields.Char(string="Custom Backup Path")
    dekad_include_filestore = fields.Boolean(string="Include Filestore")

    @api.model
    def default_get(self, fields_list):
        """Load CURRENT GLOBAL values from dekad.backup.config."""
        res = super().default_get(fields_list)
        config = self.env["dekad.backup.config"].get_config()
        res.update(
            dekad_backup_enabled=config.dekad_backup_enabled,
            dekad_backup_daily=config.dekad_backup_daily,
            dekad_backup_time=config.dekad_backup_time,
            dekad_backup_end_time=config.dekad_backup_end_time,
            dekad_backup_per_day=config.dekad_backup_per_day,
            dekad_backup_keep_count=config.dekad_backup_keep_count,
            dekad_backup_path=config.dekad_backup_path,
            dekad_include_filestore=config.dekad_include_filestore,
        )
        return res

    def action_save_settings(self):
        """Persist values GLOBALLY."""
        self.ensure_one()
        config = self.env["dekad.backup.config"].get_config()
        config.write(
            {
                "dekad_backup_enabled": self.dekad_backup_enabled,
                "dekad_backup_daily": self.dekad_backup_daily,
                "dekad_backup_time": self.dekad_backup_time,
                "dekad_backup_end_time": self.dekad_backup_end_time,
                "dekad_backup_per_day": self.dekad_backup_per_day,
                "dekad_backup_keep_count": self.dekad_backup_keep_count,
                "dekad_backup_path": self.dekad_backup_path,
                "dekad_include_filestore": self.dekad_include_filestore,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Saved",
                "message": "Global backup settings saved successfully.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_run_backup_now(self):
        """Trigger immediate backup via centralized config."""
        self.ensure_one()
        config = self.env["dekad.backup.config"].get_config()
        config._run_single_backup(trigger='manual')
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Backup created",
                "message": "Database backup was created successfully (Global settings).",
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_backup_logs(self):
        """Open the backup logs list view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Backup Logs",
            "res_model": "dekad.backup.log",
            "view_mode": "list,form",
            "target": "current",
        }
