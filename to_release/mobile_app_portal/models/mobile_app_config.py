from odoo import models, fields

class MobileAppConfig(models.Model):
    _name = 'mobile.app.config'
    _description = 'Mobile Application Configuration'
    _order = 'name'

    name = fields.Char(string="App Name", required=True, translate=True)
    technical_name = fields.Char(string="Technical Name", required=True)
    is_active = fields.Boolean(string="Is Active", default=True, help="Toggle to globally enable/disable this feature in the mobile app dashboard")
    icon = fields.Char(string="Icon Name", default="default", help="Icon identifier used on the mobile dashboard (e.g. font_awesome, material design or custom string)")
    description = fields.Text(string="Description")
    
    # Map the app config to security groups that are allowed to see it
    allowed_group_ids = fields.Many2many(
        'res.groups', 
        'mobile_app_group_rel', 
        'app_id', 
        'group_id', 
        string="Allowed Security Groups",
        help="If specified, only users belonging to one of these groups will see this app in their mobile dashboard. If left empty, all authenticated users will have access."
    )

    # Map the app config directly to specific users allowed to see it
    allowed_user_ids = fields.Many2many(
        'res.users',
        'mobile_app_user_rel',
        'app_id',
        'user_id',
        string="Allowed Users",
        help="Specifically allow these users to access this mobile app."
    )

    _sql_constraints = [
        ('technical_name_uniq', 'unique(technical_name)', 'The Technical Name of the mobile app must be unique!')
    ]
