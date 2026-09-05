# File: dekad_auto_database_backup/models/backup_config.py

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config
from datetime import datetime, time, timedelta
from pytz import timezone
import os
from odoo.service import db as db_service
import logging
import tempfile
import shutil

_logger = logging.getLogger(__name__)


class DekadBackupConfig(models.Model):
    """
    Centralized configuration for database backups. 
    Global settings for the entire database.
    """
    _name = "dekad.backup.config"
    _description = "Centralized Database Backup Configuration"

    dekad_backup_enabled = fields.Boolean(
        string="Enable automatic database backups",
        default=False,
    )
    dekad_backup_daily = fields.Boolean(
        string="Repeat backup every day",
        default=True,
    )
    dekad_backup_time = fields.Char(
        string="First backup time (HH:MM)",
        default="08:00",
    )
    dekad_backup_end_time = fields.Char(
        string="Last backup time (HH:MM)",
        default="23:59",
    )
    dekad_backup_per_day = fields.Integer(
        string="Backups per day",
        default=1,
    )
    dekad_backup_keep_count = fields.Integer(
        string="Number of backups to keep",
        default=16,
    )
    dekad_last_backup_at = fields.Datetime(
        string="Last backup datetime",
    )
    dekad_backup_path = fields.Char(
        string="Custom Backup Path",
        help="Absolute path to store backup files. If empty, defaults to <data_dir>/backups/<dbname>.",
    )
    dekad_include_filestore = fields.Boolean(
        string="Include Filestore",
        default=True,
    )

    @api.model
    def get_config(self):
        """Return the singleton record, creating it if it doesn't exist."""
        config_rec = self.search([], limit=1)
        if not config_rec:
            config_rec = self.create({})
        return config_rec

    @api.constrains('dekad_backup_per_day', 'dekad_backup_keep_count')
    def _check_backup_limits(self):
        for record in self:
            if not (1 <= record.dekad_backup_per_day <= 24):
                raise ValidationError("The number of backups per day must be between 1 and 24.")
            if record.dekad_backup_keep_count < 1:
                raise ValidationError("The number of backups to keep must be at least 1.")

    @api.constrains('dekad_backup_time', 'dekad_backup_end_time')
    def _check_backup_times(self):
        for record in self:
            start = self._parse_time_str(record.dekad_backup_time, None, None)
            end = self._parse_time_str(record.dekad_backup_end_time, None, None)
            
            if start is None:
                raise ValidationError("Invalid start time format (%s). Please use HH:MM." % record.dekad_backup_time)
            if end is None:
                raise ValidationError("Invalid end time format (%s). Please use HH:MM." % record.dekad_backup_end_time)
            if start >= end:
                raise ValidationError("The end time (%s) must be strictly after the start time (%s)." % (record.dekad_backup_end_time, record.dekad_backup_time))

    def _get_tz(self):
        """Return a pytz timezone; Force UAE time (Asia/Dubai)."""
        return timezone("Asia/Dubai")

    def _parse_time_str(self, time_str, default_hour=2, default_minute=0):
        if not time_str or not isinstance(time_str, str):
            return time(hour=default_hour, minute=default_minute) if default_hour is not None else None
        value = time_str.strip()
        if ":" not in value:
            return time(hour=default_hour, minute=default_minute) if default_hour is not None else None
        try:
            parts = value.split(":")
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return time(hour=hour, minute=minute)
        except (ValueError, TypeError, IndexError):
            pass
        return time(hour=default_hour, minute=default_minute) if default_hour is not None else None

    def _compute_today_slots(self, now_tz):
        start_time = self._parse_time_str(self.dekad_backup_time, 2, 0)
        end_time = self._parse_time_str(self.dekad_backup_end_time, 23, 59)
        per_day = max(1, self.dekad_backup_per_day or 1)

        start_dt = now_tz.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        end_dt = now_tz.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)

        if end_dt < start_dt:
            return [start_dt]

        total_minutes = (end_dt - start_dt).total_seconds() / 60
        if per_day == 1:
            slots = [start_dt]
        else:
            interval = total_minutes / (per_day - 1)
            slots = []
            for i in range(per_day):
                dt = start_dt + timedelta(minutes=interval * i)
                slots.append(dt)
        return slots

    def _run_single_backup(self, trigger='manual'):
        """Main backup execution logic moved here."""
        dbname = self.env.cr.dbname
        started_at = fields.Datetime.now()

        if self.dekad_backup_path:
            backup_dir = self.dekad_backup_path
        else:
            base_data_dir = config["data_dir"]
            backup_root = base_data_dir.replace("storage", "backups")
            backup_dir = os.path.join(backup_root, dbname)

        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            self._create_log(dbname, "failed", trigger, started_at, message=f"Could not create directory {backup_dir}: {e}")
            return

        # Disk space logging removed as per user request

        tz = self._get_tz()
        now_tz = datetime.now(tz)
        ts = now_tz.strftime("%Y-%m-%d_%H-%M-%S")
        backup_format = 'zip' if self.dekad_include_filestore else 'dump'
        ext = 'zip' if self.dekad_include_filestore else 'dump'
        filename = f"{dbname}_{ts}.{ext}"
        backup_path = os.path.join(backup_dir, filename)

        _logger.info("Creating database backup: %s (format=%s)", backup_path, backup_format)
        
        try:
            try:
                with open(backup_path, 'wb') as tfile:
                    db_service.dump_db(dbname, tfile, backup_format)
                
                file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                finished_at = fields.Datetime.now()
                duration = (finished_at - started_at).total_seconds()

                schedule_details = ""
                if trigger == 'cron':
                    try:
                        slots = self._compute_today_slots(now_tz)
                        sorted_slots = sorted(slots)
                        total_backups = len(sorted_slots)
                        closest_slot = min(sorted_slots, key=lambda s: abs((s - now_tz).total_seconds()))
                        closest_slot_str = closest_slot.strftime('%H:%M')
                        current_index = sorted_slots.index(closest_slot) + 1
                        remaining = total_backups - current_index
                        slot_strs = [s.strftime("%H:%M") for s in sorted_slots]
                        schedule_str = ", ".join(slot_strs)
                        schedule_details = (
                            f"\n\n--- Backup Schedule Info ---\n"
                            f"Configured Window: {self.dekad_backup_time} to {self.dekad_backup_end_time}\n"
                            f"Total Scheduled: {total_backups}\n"
                            f"Schedule: {schedule_str}\n"
                            f"This Backup: ~#{current_index} of {total_backups} (Allocated Slot: {closest_slot_str})\n"
                            f"Remaining Today: {remaining}"
                        )
                    except Exception as log_err:
                        _logger.warning("Failed to compute schedule details for log: %s", log_err)

                self._create_log(
                    dbname, "success", trigger, started_at,
                    finished_at=finished_at, duration=duration,
                    file_path=backup_path, file_size_mb=file_size_mb,
                    message=f"Backup successful.{schedule_details}"
                )
                self._cleanup_old_backups(backup_dir)
            except Exception:
                if os.path.exists(backup_path):
                    try: os.unlink(backup_path)
                    except OSError: pass
                raise
        except Exception as e:
            self._create_log(dbname, "failed", trigger, started_at, message=f"Backup failed: {e}")
            _logger.exception("Backup failed.")

    def _create_log(self, db_name, state, trigger, started_at, finished_at=None, duration=0.0, file_path="", file_size_mb=0.0, message=""):
        self.env["dekad.backup.log"].create({
            "db_name": db_name, "state": state, "trigger": trigger,
            "started_at": started_at, "finished_at": finished_at,
            "duration_seconds": duration, "file_path": file_path,
            "file_size_mb": file_size_mb, "message": message,
        })

    def _cleanup_old_backups(self, backup_dir):
        keep = self.dekad_backup_keep_count or 0
        if keep <= 0: return
        try:
            files = [f for f in os.listdir(backup_dir) if f.endswith(".zip") or f.endswith(".dump")]
        except FileNotFoundError: return
        prefix = f"{self.env.cr.dbname}_"
        backup_files = [f for f in files if f.startswith(prefix)]
        if len(backup_files) <= keep: return
        backup_files.sort(key=lambda fname: os.path.getmtime(os.path.join(backup_dir, fname)), reverse=True)
        to_delete = backup_files[keep:]
        for fname in to_delete:
            full_path = os.path.join(backup_dir, fname)
            try:
                os.remove(full_path)
                _logger.info("Removed old backup file: %s", full_path)
            except Exception as e:
                _logger.warning("Could not remove old backup file %s: %s", full_path, e)
