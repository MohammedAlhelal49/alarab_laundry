# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _company_visibility_domain(self):
        """ Same visibility rule as ProductTemplate/ProductProduct
        name_search/web_search_read overrides (see that module's
        docstrings for the full rationale), reused here because this
        model performs its OWN internal `search()` calls on
        product.product directly in Python - these do NOT go through
        name_search/web_search_read at all, so they need this domain
        added explicitly, on a per-method basis. """
        return ['|',
            ('company_visibility_ids', '=', False),
            ('company_visibility_ids', 'in', self.env.companies.ids),
        ]

    @api.model
    def create_expense_from_attachments(self, attachment_ids=None, view_type='list'):
        """ Full override (not a thin domain patch) of the base method:
        the original hard-codes a single `self.env['product.product']
        .search([('can_be_expensed', '=', True)])` call with no company
        filter at all, then picks the "EXP_GEN" default_code product or
        just the first result - meaning a duplicated "EXP_GEN" product
        belonging to a different company than the one the user is
        currently working under could silently be picked as the default
        Category for every expense generated from an uploaded receipt.

        This override is identical to the base implementation except for
        one line: the `search()` domain now also excludes products not
        visible to the user's active company/companies.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided"))
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        expenses = self.env['hr.expense']
        if any(attachment.res_id or attachment.res_model != 'hr.expense' for attachment in attachments):
            raise UserError(_("Invalid attachments!"))
        domain = expression.AND([
            [('can_be_expensed', '=', True)],
            self._company_visibility_domain(),
        ])
        product = self.env['product.product'].search(domain)
        if product:
            product = product.filtered(lambda p: p.default_code == "EXP_GEN")[:1] or product[0]
        else:
            raise UserError(_("You need to have at least one category that can be expensed in your database to proceed!"))
        for attachment in attachments:
            attachment_name = '.'.join(attachment.name.split('.')[:-1])
            vals = {
                'name': attachment_name,
                'price_unit': 0,
                'product_id': product.id,
            }
            if product.property_account_expense_id:
                vals['account_id'] = product.property_account_expense_id.id
            expense = self.env['hr.expense'].create(vals)
            attachment.write({'res_model': 'hr.expense', 'res_id': expense.id})
            expense._message_set_main_attachment_id(attachment, force=True)
            expenses += expense
        return {
            'name': _('Generate Expenses'),
            'res_model': 'hr.expense',
            'type': 'ir.actions.act_window',
            'views': [[False, view_type], [False, "form"]],
            'domain': [('id', 'in', expenses.ids)],
            'context': self.env.context,
        }

    @api.model
    def _parse_product(self, expense_description):
        """ Same fix as create_expense_from_attachments, applied to the
        email-based expense creation flow (`_parse_product` matches a
        product by its default_code against the first word of the email
        subject/description). Without this, an expense created by email
        could silently be attributed to a product belonging to a
        different company than the sender's employee record's company. """
        product_code = expense_description.split(' ')[0]
        domain = expression.AND([
            [('can_be_expensed', '=', True), ('default_code', '=ilike', product_code)],
            self._company_visibility_domain(),
        ])
        product = self.env['product.product'].search(domain, limit=1)
        if product:
            expense_description = expense_description.replace(product_code, '', 1)
        return product, expense_description
