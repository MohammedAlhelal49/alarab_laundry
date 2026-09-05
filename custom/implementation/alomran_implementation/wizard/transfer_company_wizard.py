from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TransferCompanyWizard(models.TransientModel):
    _name = 'transfer.company.wizard'
    _description = 'Transfer User Leads and Contacts'

    user_id = fields.Many2one(
        'res.users',
        required=True,
        readonly=True
    )

    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
        required=True
    )

    contact_count = fields.Integer(
        compute='_compute_counts',
        string='Contacts'
    )

    lead_count = fields.Integer(
        compute='_compute_counts',
        string='Leads'
    )

    @api.depends('user_id', 'target_company_id')
    def _compute_counts(self):
        for wizard in self:

            wizard.contact_count = self.env['res.partner'].search_count([
                ('user_id', '=', wizard.user_id.id),
                '|',
                ('company_id', '=', False),
                ('company_id', '!=', wizard.target_company_id.id),
            ])

            wizard.lead_count = self.env['crm.lead'].search_count([
                ('user_id', '=', wizard.user_id.id),
                ('company_id', '!=', wizard.target_company_id.id),
            ])

    def action_transfer(self):
        self.ensure_one()

        if not self.target_company_id:
            raise UserError(_("Please select a target company."))

        target_company = self.target_company_id

        # GET LEADS FIRST
        leads = self.env['crm.lead'].search([
            ('user_id', '=', self.user_id.id),
            ('company_id', '!=', target_company.id),
        ])

        # GET ALL RELATED CUSTOMERS
        partners = self.env['res.partner']

        # customers assigned directly to salesperson
        salesperson_partners = self.env['res.partner'].search([
            ('user_id', '=', self.user_id.id),
        ])

        partners |= salesperson_partners

        # customers linked to opportunities
        lead_partners = leads.mapped('partner_id')

        partners |= lead_partners

        # include child contacts
        partners |= partners.mapped('child_ids')

        # include commercial partners
        partners |= partners.mapped('commercial_partner_id')

        # remove duplicates
        partners = partners.exists()

        #UPDATE CUSTOMERS FIRST

        for partner in partners:
            partner.write({
                'company_id': target_company.id
            })

        self.env.cr.commit()
        self.env.invalidate_all()

        # RELOAD LEADS AFTER COMMIT

        leads = self.env['crm.lead'].browse(leads.ids)

        #UPDATE LEADS

        for lead in leads:
            lead.write({
                'company_id': target_company.id
            })

        self.env.cr.commit()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Completed'),
                'message': _(
                    '%s contacts and %s leads transferred to %s.'
                ) % (
                    len(partners),
                    len(leads),
                    target_company.name
                ),
                'sticky': False,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }