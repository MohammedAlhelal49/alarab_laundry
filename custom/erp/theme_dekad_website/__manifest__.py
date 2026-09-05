# -*- coding: utf-8 -*-
{
    'name': 'Dekad Official Website Theme',
    'version': '1.0',
    'category': 'Theme/Creative',
    'summary': 'Custom brand identity and CRM-integrated lead generation for Dekad.',
    'description': """
        This module implements the new visual identity for Dekad.
        Key Features:
        - Simplified navigation bar with dual CTAs.
        - Engaging hero section and categorized 'Our Clients' layout.
        - Custom '/request-demo' page with automated CRM lead creation.
        - Integrated WhatsApp business widget.
    """,
    'author': 'Dekad (Mofeed Dozkanji)',
    'website': 'https://www.dekad.tech',
    'depends': [
        'website',
        'crm',
        'website_crm',
        'project',
        'helpdesk',
        'http_routing',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/crm_lead_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/website_demo_templates.xml',
        'views/website_layout_templates.xml',
        'views/website_pages_views.xml',
        'views/error_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_dekad_website/static/src/scss/main.scss',
        ],
    },
    'images': [
        'static/description/theme_screenshot.jpeg',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
