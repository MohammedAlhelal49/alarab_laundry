from odoo import models, fields, api, tools


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_activity_tracked = fields.Boolean(string="Track Activity", default=False)

    def write(self, vals):
        res = super().write(vals)
        # Clear the cache if tracking settings change
        if 'is_activity_tracked' in vals:
            self.env['base']._clear_tracked_models_cache()
        return res

    @api.model
    def action_sync_logger_defaults(self):
        """Manual trigger to re-apply default tracking."""
        from ..hooks import post_init_hook
        post_init_hook(self.env)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Default tracking has been applied to available models.',
                'type': 'success',
                'sticky': False,
            }
        }
