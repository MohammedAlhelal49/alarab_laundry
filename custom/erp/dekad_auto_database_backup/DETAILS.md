# Dekad Auto Database Backup
**Version:** 18.0.1.0.0  
**Author:** Mohammed Khair (Dekad)

## Overview
This module provides a robust, fully automated solution for backing up your Odoo database. It allows for configurable schedules, retention policies, and detailed logging, ensuring your data is safe without manual intervention.

## Key Features

### 1. Automated Scheduling
- **Customizable Intervals:** Define how many times per day you want to backup your database (up to 8 times).
- **Time Windows:** Set a start time and end time (e.g., 08:00 AM to 06:00 PM) to ensure backups run only during desired hours.
- **Smart Calculation:** The module automatically divides your time window by the number of backups to create evenly spaced slots.
- **Timezone Aware:** All schedules are calculated based on the configured timezone (Default: Asia/Dubai).

### 2. Manual Backups
- Trigger an immediate backup anytime from the Settings menu.
- Manual backups are logged separately and do not interfere with your daily scheduled count or retention statistics.

### 3. Smart Retention & Cleanup
- **Auto-Cleanup:** configure the "Number of backups to keep". The module automatically deletes the oldest backups to save disk space, keeping only the most recent N files.
- **Disk Space Safety:** The system checks for available disk space before running operations.

### 4. Comprehensive Logging
- Every backup operation (success or failure) is logged.
- **Detailed Schedule Info:** Scheduled backup logs show exactly which slot was executed (e.g., *"Backup #1 of 3 (Allocated Slot: 08:00)"*) and how many are remaining for the day.
- **Manual Backup Distinction:** Manual backups are clearly marked to avoid confusion with the automated schedule.
- **Download Access:** Authorized users can download backup files directly from the log view.

## Configuration
Go to **Settings** -> **Technical** -> **Database Backup** to configure:
- **Enable Backups:** Master switch.
- **Backup Path:** (Optional) Custom path to store files. Defaults to your Odoo data directory.
- **Include Filestore:** Option to include attachments (zip) or just the database dump (sql).
- **Schedule Parameters:** Daily, Start Time, End Time, Count per Day.

## Technical Notes
- **Permissions:** A dedicated "Backup User" group controls who can view logs and download files. This permission is **not** granted to all users by default for security.
- **Format:** Supports both `.zip` (with filestore) and `.dump` (SQL only) formats.

---
*Developed with care by Mohammed Khair*
