# File: dekad_auto_database_backup/models/res_company.py

from odoo import api, fields, models
import logging
import os
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    # DEPRECATED: These fields are now handled centrally in dekad.backup.config
    # Keeping them for compatibility/migration but they should be ignored.
    dekad_backup_enabled = fields.Boolean(string="Enable automatic database backups (Deprecated)")
    dekad_backup_daily = fields.Boolean(string="Repeat backup every day (Deprecated)")
    dekad_backup_time = fields.Char(string="First backup time (HH:MM) (Deprecated)")
    dekad_backup_end_time = fields.Char(string="Last backup time (HH:MM) (Deprecated)")
    dekad_backup_per_day = fields.Integer(string="Backups per day (Deprecated)")
    dekad_backup_keep_count = fields.Integer(string="Number of backups to keep (Deprecated)")
    dekad_last_backup_at = fields.Datetime(string="Last backup datetime (Deprecated)")
    dekad_backup_path = fields.Char(string="Custom Backup Path (Deprecated)")
    dekad_include_filestore = fields.Boolean(string="Include Filestore (Deprecated)")

    @api.model
    def run_scheduled_backups(self):
        """
        Called by ir.cron.
        Delegates schedule check and backup execution to dekad.backup.config.
        Includes auto-migration from legacy multi-company settings.
        """
        ConfigModel = self.env["dekad.backup.config"]
        config = ConfigModel.get_config()
        
        # --- AUTO MIGRATION LOGIC ---
        # If the central config is disabled and no last backup timestamp exists,
        # try to find a legacy company that was active and migrate its settings.
        if not config.dekad_backup_enabled and not config.dekad_last_backup_at:
            legacy_company = self.sudo().search([('dekad_backup_enabled', '=', True)], order='id asc', limit=1)
            if legacy_company:
                _logger.info("[backup] MIGRATING settings from legacy company %s (ID: %s) to Centralized Config.", legacy_company.name, legacy_company.id)
                config.write({
                    "dekad_backup_enabled": True,
                    "dekad_backup_daily": legacy_company.dekad_backup_daily,
                    "dekad_backup_time": legacy_company.dekad_backup_time,
                    "dekad_backup_end_time": legacy_company.dekad_backup_end_time,
                    "dekad_backup_per_day": legacy_company.dekad_backup_per_day,
                    "dekad_backup_keep_count": legacy_company.dekad_backup_keep_count,
                    "dekad_last_backup_at": legacy_company.dekad_last_backup_at,
                    "dekad_backup_path": legacy_company.dekad_backup_path,
                    "dekad_include_filestore": legacy_company.dekad_include_filestore,
                })
                # Disable all legacy company backups to avoid double migration
                self.sudo().search([('dekad_backup_enabled', '=', True)]).write({'dekad_backup_enabled': False})

        # --- EXECUTION LOGIC ---
        if not config.dekad_backup_enabled:
            _logger.info("[backup] Centralized database backup is disabled.")
            return

        tz = config._get_tz()
        now_utc = fields.Datetime.now()
        now_tz = now_utc.astimezone(tz)
        last_utc = config.dekad_last_backup_at
        last_tz = last_utc.astimezone(tz) if last_utc else None

        slots = config._compute_today_slots(now_tz)
        _logger.info(
            "[backup] SYSTEM-WIDE BACKUP: now=%s last=%s slots=%s",
            now_tz, last_tz, [s.strftime("%H:%M") for s in slots if s],
        )

        due_slots = [slot for slot in slots if slot <= now_tz]
        if not due_slots: return

        target_slot = max(due_slots)
        if last_tz and last_tz >= target_slot:
            _logger.info("[backup] Already ran for the most recent slot %s.", target_slot.strftime("%H:%M"))
            return

        # Run backup now via centralized config model
        try:
            config._run_single_backup(trigger='cron')
            config.write({"dekad_last_backup_at": now_utc})
        except Exception as e:
            _logger.exception("Centralized backup failed: %s", e)

        # One-time mode: disable backups after the first execution
        if not config.dekad_backup_daily:
            config.write({"dekad_backup_enabled": False})

    @api.model
    def clean_database_backup(self):
        """Delegates daily cleanup to dekad.backup.config."""
        # Cleanup logs older than 170 days
        limit_date = fields.Datetime.now() - timedelta(days=170)
        old_logs = self.env['dekad.backup.log'].sudo().search([('started_at', '<', limit_date)])
        if old_logs:
            _logger.info("[backup] Cleaning up %d old logs.", len(old_logs))
            old_logs.unlink()

        config = self.env["dekad.backup.config"].get_config()
        if config.dekad_backup_enabled:
            # Re-calculate backup dir
            if config.dekad_backup_path:
                backup_dir = config.dekad_backup_path
            else:
                from odoo.tools import config as odoo_config
                base_data_dir = odoo_config["data_dir"]
                backup_root = base_data_dir.replace("storage", "backups")
                backup_dir = os.path.join(backup_root, self.env.cr.dbname)
            
            config._cleanup_old_backups(backup_dir)

    # Legacy method compatibility
    @api.model
    def backup_database(self):
        self.run_scheduled_backups()
