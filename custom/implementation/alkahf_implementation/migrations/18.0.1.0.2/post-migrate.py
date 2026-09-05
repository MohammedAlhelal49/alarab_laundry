from odoo import api, SUPERUSER_ID


def migrate(cr, version):

    env = api.Environment(cr, SUPERUSER_ID, {})

    companies = env['res.company'].search([])

    for company in companies:

        moves = env['account.move'].search([
            ('company_id', '=', company.id),
            ('serial_number', '=', False),
            ('state', '=', 'posted'),

        ], order='date asc, id asc')

        counter = 1

        prefix = company.move_serial_prefix or 'JV'

        for move in moves:

            move.serial_number = (
                f"{prefix}/{str(counter).zfill(6)}"
            )

            counter += 1