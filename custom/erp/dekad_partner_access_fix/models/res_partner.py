# -*- coding: utf-8 -*-
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _apply_customer_dropdown_filter(self, domain):
        """Append the salesperson filter when the call originates from a
        context that uses res_partner_search_mode='customer' (CRM
        widgets, Sales Customers page, etc.).
        """
        if self.env.context.get('res_partner_search_mode') == 'customer':
            extra = [('user_id', '=', self.env.uid)]
            return list(domain) + extra if domain else extra
        return domain

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign the current user as salesperson when creating a
        partner from a 'customer' context (CRM dropdowns, Sales
        Customers page, etc.) and no salesperson was provided.

        Without this, the newly created partner would have user_id=False
        and would immediately disappear from the creator's view because
        of the filter in _apply_customer_dropdown_filter. Auto-assigning
        keeps the partner visible and reflects reality: whoever created
        it is responsible for it, unless explicitly set otherwise.
        """
        if self.env.context.get('res_partner_search_mode') == 'customer':
            for vals in vals_list:
                if not vals.get('user_id'):
                    vals['user_id'] = self.env.uid
        return super().create(vals_list)

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0,
                        limit=None, order=None, count_limit=None):
        """Scope the initial dropdown/list (shown before the user types)
        to partners assigned to the current user.
        """
        domain = self._apply_customer_dropdown_filter(domain)
        return super().web_search_read(
            domain=domain, specification=specification, offset=offset,
            limit=limit, order=order, count_limit=count_limit,
        )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Scope typed-in searches for consistency with web_search_read."""
        args = self._apply_customer_dropdown_filter(args)
        return super().name_search(
            name=name, args=args, operator=operator, limit=limit,
        )