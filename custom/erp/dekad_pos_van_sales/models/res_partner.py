from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Load POS customers depending on whether user is a driver
    @api.model
    def _load_pos_data_domain(self, data):
        user = self.env.user
        user_id = user.id
        user_partner_id = user.partner_id.id

        # Check if the user is a driver in any van.assignment
        is_driver = self.env['van.assignment'].search_count([
            ('driver_id.related_user_id', '=', user_id)
        ]) > 0

        records = self.env['van.assignment'].search([]).mapped('driver_id')
        for rec in records:
            print(rec.related_user_id)

        print(is_driver)
        print(user_id)

        # If not a driver, return all customers (no domain)
        if not is_driver:
            return []

        # If user is a driver, return only assigned customers (excluding themselves)
        assigned_partner_ids = self.env['van.assignment.customer'].search(
            [('assignment_id.driver_id.related_user_id', '=', user_id)]).mapped('partner_id.id')

        # Remove user's own partner if present
        filtered_partner_ids = list(set(assigned_partner_ids) - {user_partner_id})

        return [('id', 'in', filtered_partner_ids)]
