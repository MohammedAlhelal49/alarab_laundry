from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    fcm_device_ids = fields.One2many('fcm.device', 'partner_id', related='partner_id.fcm_device_ids', string='FCM Devices', readonly=False)
