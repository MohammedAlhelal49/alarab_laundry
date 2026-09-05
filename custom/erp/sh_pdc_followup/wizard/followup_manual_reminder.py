from odoo import api, fields, models, Command


class PdcFollowupManualReminder(models.TransientModel):
    _name = 'pdc.followup.manual_reminder'
    _inherit = 'mail.composer.mixin'
    _description = "Wizard for sending manual PDC follow-up reminders"

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        assert self.env.context['active_model'] == 'res.partner'
        partner = self.env['res.partner'].browse(self.env.context['active_ids'])
        partner.ensure_one()
        followup_line = partner.pdc_followup_line_id
        if followup_line:
            defaults.update(
                email=followup_line.send_email,
                sms=followup_line.send_sms,
                template_id=followup_line.mail_template_id.id,
                sms_template_id=followup_line.sms_template_id.id,
                join_invoices=followup_line.join_invoices,
            )
        defaults.update(
            partner_id=partner.id,
            render_model='res.partner',
        )
        return defaults

    partner_id = fields.Many2one(comodel_name='res.partner')

    # email fields
    email = fields.Boolean()
    email_recipient_ids = fields.Many2many(
        string="Extra Recipients",
        comodel_name='res.partner',
        compute='_compute_email_recipient_ids',
        store=True,
        readonly=False,
        relation='rel_pdc_followup_manual_reminder_res_partner',
    )

    # sms fields
    sms = fields.Boolean()
    sms_body = fields.Char(compute='_compute_sms_body', readonly=False, store=True)
    sms_template_id = fields.Many2one(comodel_name='sms.template', domain=[('model', '=', 'res.partner')])

    # print fields
    print = fields.Boolean(default=True)
    join_invoices = fields.Boolean(string="Attach PDC Documents")

    # attachments fields
    attachment_ids = fields.Many2many(comodel_name='ir.attachment')

    def _compute_render_model(self):
        # OVERRIDES mail.renderer.mixin
        self.render_model = 'res.partner'

    @api.depends('template_id')
    def _compute_subject(self):
        for wizard in self:
            options = {
                'partner_id': wizard.partner_id.id,
                'mail_template': wizard.template_id,
            }
            wizard.subject = self.env['pdc.followup.report']._get_email_subject(options)

    @api.depends('template_id')
    def _compute_body(self):
        # OVERRIDES mail.composer.mixin
        for wizard in self:
            options = {
                'partner_id': wizard.partner_id.id,
                'mail_template': wizard.template_id,
            }
            wizard.body = self.env['pdc.followup.report']._get_main_body(options)

    @api.depends('template_id')
    def _compute_email_recipient_ids(self):
        for wizard in self:
            partner = wizard.partner_id
            template = wizard.template_id
            wizard.email_recipient_ids = partner
            if template:
                rendered_values = template._generate_template_recipients(
                    [partner.id],
                    {'partner_to', 'email_cc', 'email_to'},
                    True
                )[partner.id]
                if rendered_values.get('partner_ids'):
                    wizard.email_recipient_ids = [
                        Command.link(partner_id)
                        for partner_id in rendered_values['partner_ids']
                    ]

    @api.depends('sms_template_id')
    def _compute_sms_body(self):
        for wizard in self:
            options = {
                'partner_id': wizard.partner_id.id,
                'sms_template': wizard.sms_template_id,
            }
            wizard.sms_body = self.env['pdc.followup.report']._get_sms_body(options)

    def _get_wizard_options(self):
        return {
            'partner_id': self.partner_id,
            'email': self.email,
            'email_from': self.template_id.email_from if self.template_id else False,
            'email_subject': self.subject,
            'email_recipient_ids': self.email_recipient_ids,
            'body': self.body,
            'attachment_ids': self.attachment_ids.ids,
            'sms': self.sms,
            'sms_body': self.sms_body,
            'print': self.print,
            'join_invoices': self.join_invoices,
            'manual_followup': True,
        }

    def process_followup(self):
        options = self._get_wizard_options()
        options['author_id'] = self.env.user.partner_id.id
        action = self.partner_id.execute_pdc_followup(options)
        return action or {'type': 'ir.actions.act_window_close'}
