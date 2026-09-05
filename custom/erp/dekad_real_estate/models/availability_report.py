from odoo import models, fields, tools, api


class RealEstatePropertyAvailabilityReport(models.Model):
    _name = 'real.estate.property.availability.report'
    _description = 'Property Availability Report'
    _auto = False
    _order = 'is_available asc, days_left asc'

    property_id = fields.Many2one('account.analytic.account', string='Property', readonly=True)
    building_id = fields.Many2one('real.estate.buildings', string='Building', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    is_available = fields.Boolean(string='Available', readonly=True)
    rental_contract_count = fields.Integer(string='Rental Contracts', readonly=True)
    current_contract_id = fields.Many2one('sale.order', string='Current Contract', readonly=True)
    current_contract_rent_state = fields.Selection([
        ('not_booked', "Not Booked"),
        ('booked', "Booked"),
        ('not_paid', "Not Paid"),
        ('partially_paid', "Partially Paid"),
        ('paid', "Paid"),
        ('cancel', "Cancelled"),
    ], string='Contract Status', readonly=True)
    rent_start_date = fields.Date(string='Contract Start', readonly=True)
    rent_end_date = fields.Date(string='Contract End', readonly=True)
    days_left = fields.Integer(string='Days Left', readonly=True)
    availability_status = fields.Selection([
        ('available', 'Available'),
        ('rented', 'Rented'),
    ], string='Availability', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    property.id                      AS id,
                    property.id                      AS property_id,
                    building.id                       AS building_id,
                    property.company_id               AS company_id,
                    CASE
                        WHEN current_contract.id IS NOT NULL
                        THEN FALSE
                        ELSE TRUE
                    END                                 AS is_available,
                    CASE
                        WHEN current_contract.id IS NOT NULL
                        THEN 'rented'
                        ELSE 'available'
                    END AS availability_status,
                    COALESCE(contract_count.cnt, 0)    AS rental_contract_count,
                    current_contract.id                AS current_contract_id,
                    current_contract.rent_state        AS current_contract_rent_state,
                    current_contract.rent_start_date   AS rent_start_date,
                    current_contract.rent_end_date     AS rent_end_date,
                    CASE
                        WHEN current_contract.rent_end_date IS NOT NULL
                        THEN (current_contract.rent_end_date - CURRENT_DATE)
                        ELSE NULL
                    END AS days_left
                FROM account_analytic_account property
                LEFT JOIN real_estate_buildings building
                    ON building.id = property.property_building_id
                LEFT JOIN LATERAL (
                    SELECT
                        so.id,
                        so.rent_state,
                        so.rent_start_date,
                        so.rent_end_date
                    FROM sale_order so
                    WHERE so.account_analytic_account_id = property.id
                        AND so.state = 'sale'
                        AND COALESCE(so.is_closed, FALSE) = FALSE
                        AND so.rent_state IN ('booked', 'not_paid', 'partially_paid', 'paid')
                        AND CURRENT_DATE BETWEEN so.rent_start_date AND so.rent_end_date
                    ORDER BY so.rent_start_date DESC
                    LIMIT 1
                ) current_contract ON TRUE
                LEFT JOIN (
                    SELECT account_analytic_account_id, COUNT(*) AS cnt
                    FROM sale_order
                    WHERE account_analytic_account_id IS NOT NULL
                    GROUP BY account_analytic_account_id
                ) contract_count ON contract_count.account_analytic_account_id = property.id
                WHERE property.is_property = TRUE
                    AND property.offer_type = 'rent'
            )
        """)

    def action_open_contract(self):
        self.ensure_one()
        if not self.current_contract_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rental Contract',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.current_contract_id.id,
            'target': 'current',
            'context': {'rental_mode': True},
        }