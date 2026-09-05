# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.payment_telr import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('telr', 'Telr')], ondelete={'telr': 'set default'})
    telr_merchant_id = fields.Char(string='Store ID', required_if_provider='telr', groups='base.group_user')
    telr_api_key = fields.Char('Authentication Key', required_if_provider='telr', groups='base.group_user')
    telr_lang = fields.Selection(string='Language',selection = [('en', 'English'),('ar', 'Arabic')],selection_add=[('en', 'English'),('ar', 'Arabic')],ondelete={'en': 'set default'},required_if_provider='telr',groups='base.group_user')
    telr_payment_mode = fields.Selection(string='Payment Mode',selection = [('0', 'Standard'),('2', 'iFrame'),('10', 'Seamless')],selection_add=[('0', 'Standard'),('2', 'iFrame'),('10', 'Seamless')],ondelete={'0': 'set default'},required_if_provider='telr',groups='base.group_user')
    telr_remote_key = fields.Char('Remote API Authentication Key', groups='base.group_user')
    telr_trans_type = fields.Selection(string='Payment Transction Mode',selection = [('sale', 'Sale'),('auth', 'Authorised')],selection_add=[('sale', 'Sale'),('auth', 'Authorised')],ondelete={'sale': 'set default'},required_if_provider='telr',groups='base.group_user')
    
#=== COMPUTE METHODS ===#
    @api.depends('code')
    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """     
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'telr').update({
            'support_manual_capture': 'full_only',
            'support_refund': 'partial',
        })
        
    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'telr':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES    