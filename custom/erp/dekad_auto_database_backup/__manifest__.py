
{
    "name": "Dekad - Automatic Database Backup",
    "summary": "Automatic database backups with configurable schedule, cleanup and logs.",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "author": "Dekad (Mohammed Khair)",
    "website": "https://dekad.tech",
    "license": "LGPL-3",
    "depends": ["base", "web", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/backup_settings_views.xml",
        "views/backup_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
