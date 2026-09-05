from odoo import models, fields, api

class FcmAddonPreference(models.Model):
    _name = 'fcm.addon.preference'
    _description = 'FCM Addon Notification Preference'

    user_id = fields.Many2one('res.users', string='User', ondelete='cascade')
    device_id = fields.Many2one('fcm.device', string='Device', ondelete='cascade')
    module_id = fields.Many2one('ir.module.module', string='Addon', required=True, ondelete='cascade', domain=[('state', '=', 'installed')])
    is_enabled = fields.Boolean(string='Notifications Enabled', default=True)
    action_ids = fields.One2many('fcm.addon.preference.action', 'preference_id', string='Actions')

    _sql_constraints = [
        ('user_module_unique', 'unique(user_id, device_id, module_id)', 'Preference already exists for this module!')
    ]

    @api.model
    def is_notification_enabled(self, partner, model_name, action_type=None, device=None):
        """
        Check if notifications are enabled for a given partner, module (from model), action, and optionally device.
        """
        if not partner:
            return True
            
        user = partner.user_ids[:1]
        if not user:
            return True

        # Identify modules for the model
        ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        if not ir_model or not ir_model.modules:
            # Fallback for 'mail' core events
            if action_type in ['message', 'activity']:
                modules = self.env['ir.module.module'].sudo().search([('name', '=', 'mail')], limit=1)
            else:
                return True
        else:
            modules = self.env['ir.module.module'].sudo().search([('name', 'in', ir_model.modules.split(','))])

        if not modules:
            return True

        # Check Module-level preference
        domain = [
            ('user_id', '=', user.id),
            ('module_id', 'in', modules.ids),
            ('is_enabled', '=', False)
        ]
        if device:
            domain.append(('device_id', '=', device.id))
        else:
            domain.append(('device_id', '=', False)) # User-level global

        if self.sudo().search_count(domain):
            return False

        # Check Action-level preference
        if action_type:
            action_domain = [
                ('preference_id.user_id', '=', user.id),
                ('preference_id.module_id', 'in', modules.ids),
                ('action_type', '=', action_type),
                ('is_enabled', '=', False)
            ]
            if device:
                action_domain.append(('preference_id.device_id', '=', device.id))
            else:
                action_domain.append(('preference_id.device_id', '=', False))

            if self.env['fcm.addon.preference.action'].sudo().search_count(action_domain):
                return False

        return True

    def open_actions(self):
        """Open the form view for this preference to manage actions."""
        self.ensure_one()
        return {
            'name': f'Manage Actions: {self.module_id.shortdesc}',
            'type': 'ir.actions.act_window',
            'res_model': 'fcm.addon.preference',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def get_available_actions(self, module_name):
        """Return a list of available actions (events) for a given module."""
        # This map defines which actions are available for which Odoo module
        # The key is the technical name of the module
        
        # Define the actions
        sale_actions = [('created', 'New Sale Order (Quotation)'), ('confirmed', 'Sale Order Confirmed')]
        crm_actions = [('created', 'New Lead/Opp'), ('won', 'Opportunity Won'), ('assigned', 'Lead Assigned')]
        account_actions = [('created', 'New Invoice/Bill'), ('posted', 'Invoice Posted')]
        purchase_actions = [('created', 'New Purchase Order'), ('confirmed', 'PO Confirmed')]
        stock_actions = [('created', 'New Transfer'), ('done', 'Transfer Done')]
        mail_actions = [('message', 'Direct Messages/Mentions'), ('activity', 'Activities')]

        MODULE_ACTIONS = {
            'sale': sale_actions,
            'sale_management': sale_actions,
            'crm': crm_actions,
            'account': account_actions,
            'account_accountant': account_actions,
            'purchase': purchase_actions,
            'purchase_stock': purchase_actions,
            'stock': stock_actions,
            'stock_picking_batch': stock_actions,
            'mail': mail_actions,
        }
        
        # Return specific actions if defined, otherwise fallback to standard CRUD from activity.logger
        if module_name in MODULE_ACTIONS:
            return MODULE_ACTIONS[module_name]
            
        if 'activity.logger' in self.env:
            return self.env['activity.logger']._fields['operation_type'].selection
            
        return []

class FcmAddonPreferenceAction(models.Model):
    _name = 'fcm.addon.preference.action'
    _description = 'FCM Addon Action Preference'

    preference_id = fields.Many2one('fcm.addon.preference', string='Module Preference', ondelete='cascade', required=True)
    action_type = fields.Char(string='Action Type', required=True)
    action_label = fields.Char(string='Action', help='Display label for the action')
    is_enabled = fields.Boolean(string='Enabled', default=True)

    _sql_constraints = [
        ('pref_action_unique', 'unique(preference_id, action_type)', 'Action preference already exists!')
    ]
