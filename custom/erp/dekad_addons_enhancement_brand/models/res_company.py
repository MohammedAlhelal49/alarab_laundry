from odoo import models, api
import os
from pytz import timezone
from datetime import datetime
from odoo.service import db


class ResCompany(models.Model):
    _inherit = "res.company"

    def config_data(self):
        # handle the root user data
        root_user = self.env.ref('base.user_root')
        root_user.write({
            "name" : "System user" ,
            "email" : "support@dekad.tech"
        })
        # delete the data chat and Logging
        self.env['mail.message'].search([]).unlink()
        self.env['ir.logging'].sudo().search([]).unlink()

        # deactivate the digest
        self.env['digest.digest'].sudo().search([]).write({'state': 'deactivated'})

        # deactivate the digest emails
        self.env.ref('digest.ir_cron_digest_scheduler_action').write({'active': False})
        self.env.ref('digest.ir_cron_digest_scheduler_action').write({'active': False})

