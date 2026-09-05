{
    "name": "Web Enterprise Block",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Hide Odoo Enterprise Expiration Blocking Screen",
    "depends": ["web_enterprise" , "web"],
    "assets": {
        "web.assets_backend": [
            "web_enterprise_block/static/src/js/panel.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}