# Copyright 2026 Dekad (Mohammed Khair)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Dekad duplicate contact detection",
    "version": "18.0.1.0",
    "summary": "Add duplicate phone/mobile detection and CRM-Contact mobile sync to Contacts and CRM",
    "description": """
    - Detect and optionally prevent duplicate contact phone/mobile numbers, configurable from CRM Settings.
    - Show duplicate warnings on Contact and CRM Lead/Opportunity forms with access-controlled duplicate links.
    - Synchronize CRM Lead phone/mobile numbers with the linked Contact.
""",
    "author": "Dekad (smr)",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "crm"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
}
