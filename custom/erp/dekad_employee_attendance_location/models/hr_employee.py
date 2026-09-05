from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    gps_latitude = fields.Float(
        string='GPS Latitude',
        digits=(10, 7),
    )
    gps_longitude = fields.Float(
        string='GPS Longitude',
        digits=(10, 7),
    )

    gps_last_updated = fields.Datetime(
        string='Last GPS Update',
        readonly=True,
    )

    gps_location_url = fields.Char(
        string='Google Maps Link',
        compute='_compute_location_url',
        store=True,
    )

    @api.depends('gps_latitude', 'gps_longitude')
    def _compute_location_url(self):
        for rec in self:
            if rec.gps_latitude and rec.gps_longitude:
                rec.gps_location_url = f"https://www.google.com/maps?q={rec.gps_latitude},{rec.gps_longitude}"
            else:
                rec.gps_location_url = ''

    def action_get_gps_coordinates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'get_gps_coordinates',
            'context': {'employee_id': self.id},
        }

    def action_open_gps_location(self):
        self.ensure_one()
        if self.gps_location_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.gps_location_url,
                'target': 'new',
            }

    @api.model
    def update_employee_gps(self, latitude, longitude):
        employee = self.sudo().search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not employee:
            return False

        employee.sudo().write({
            'gps_latitude': float(latitude),
            'gps_longitude': float(longitude),
            'gps_last_updated': fields.Datetime.now(),
        })

        return True