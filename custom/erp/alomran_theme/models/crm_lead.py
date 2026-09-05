# -*- coding: utf-8 -*-
"""
Alomran Theme - CRM Lead Extensions
===================================
Custom fields and methods for CRM leads from website.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ============================================================
    # CUSTOM FIELDS
    # ============================================================

    x_source_type = fields.Selection([
        ('popup', 'Popup Offer'),
        ('course', 'Course Registration'),
        ('website', 'Website Form'),
        ('contact', 'Contact Form'),
        ('manual', 'Manual Entry'),
        ('other', 'Other'),
    ], string='Source Type', default='other', tracking=True)

    x_course_interest = fields.Char(
        string='Course Interest',
        tracking=True,
        help='Name of the course the customer is interested in'
    )

    x_preferred_branch = fields.Char(
        string='Preferred Branch',
        tracking=True,
        help='Customer preferred branch'
    )

    # ✅ تعريف الـ Many2one هنا فقط (بدون inverse في popup.offer)
    x_popup_offer_id = fields.Many2one(
        'popup.offer',
        string='Pop-up Offer',
        ondelete='set null',
        tracking=True,
        help='The offer through which the customer registered'
    )

    x_registration_date = fields.Datetime(
        string='Registration Date',
        default=fields.Datetime.now,
        readonly=True,
        help='Registration date and time'
    )

    # ============================================================
    # COMPUTED FIELDS
    # ============================================================

    x_source_type_display = fields.Char(
        string='Source Type Display',
        compute='_compute_source_type_display',
        store=True,
    )

    @api.depends('x_source_type')
    def _compute_source_type_display(self):
        """Compute English display name for source type."""
        labels = {
            'popup': 'Pop-up Offer',
            'course': 'Course Registration',
            'website': 'Website Form',
            'contact': 'Contact Form',
            'manual': 'Manual Entry',
            'other': 'Other',
        }
        for lead in self:
            lead.x_source_type_display = labels.get(lead.x_source_type, 'Other')

    # ============================================================
    # VALIDATION
    # ============================================================

    @api.constrains('phone', 'mobile')
    def _check_phone_format(self):
        """Validate phone number format (UAE) - warning only."""
        uae_pattern = re.compile(r'^(?:\+971|00971|0)?(?:50|51|52|54|55|56|58)\d{7}$')

        for lead in self:
            if lead.phone:
                cleaned = re.sub(r'[\s\-\(\)]', '', lead.phone)
                if not uae_pattern.match(cleaned) and not re.match(r'^05\d{8}$', cleaned):
                    _logger.warning(f"Phone may not be valid UAE format: {lead.phone}")

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _get_safe_stage_id(self, stage_xmlid='crm.stage_lead1', fallback_sequence=1):
        """Get stage ID safely with fallback."""
        stage = self.env.ref(stage_xmlid, raise_if_not_found=False)
        if stage:
            return stage.id

        stage = self.env['crm.stage'].search([
            ('sequence', '=', fallback_sequence)
        ], limit=1)

        if stage:
            return stage.id

        stage = self.env['crm.stage'].search([], limit=1, order='sequence')
        return stage.id if stage else False

    # ============================================================
    # BUSINESS METHODS
    # ============================================================

    @api.model
    def create_popup_lead(self, name, phone, offer_id=None):
        """Create lead from popup offer."""
        self = self.sudo()

        vals = {
            'name': f"Popup: {name}",
            'contact_name': name,
            'phone': phone,
            'type': 'lead',
            'x_source_type': 'popup',
            'x_registration_date': fields.Datetime.now(),
            'stage_id': self._get_safe_stage_id('crm.stage_lead1'),
            'user_id': False,
        }

        if offer_id:
            try:
                offer = self.env['popup.offer'].browse(int(offer_id))
                if offer.exists():
                    vals['x_popup_offer_id'] = offer.id
                    vals['description'] = self._build_popup_description(offer)
                else:
                    vals['description'] = self._get_default_description('popup')
            except (ValueError, TypeError):
                vals['description'] = self._get_default_description('popup')
        else:
            vals['description'] = self._get_default_description('popup')

        lead = self.create(vals)
        _logger.info(f"Popup lead created: ID={lead.id}, Name={name}")

        return lead

    def _build_popup_description(self, offer):
        """Build description from offer."""
        type_labels = {
            'buy_x_get_y': 'Buy X Get Y',
            'discount_percentage': 'Percentage Discount',
            'discount_fixed': 'Fixed Amount Discount',
            'free_consultation': 'Free Consultation',
            'custom': 'Custom Offer',
        }

        parts = [
            'Lead registered from a website Pop-up offer',
            '',
            f"📢 Offer Name: {offer.name}",
            f"🏷️ Offer Type: {type_labels.get(offer.offer_type, offer.offer_type)}",
        ]

        if offer.description_ar:
            parts.extend(['', offer.description_ar])

        parts.extend([
            '',
            '---',
            'The customer has shown interest in this offer.',
            'Please follow up within 24 hours.',
        ])

        return '\n'.join(parts)

    def _get_default_description(self, source_type):
        """Get default description by source type."""
        descriptions = {
            'popup': 'Registered from a website Pop-up offer\n\nPlease follow up within 24 hours.',
            'course': 'Course registration request\n\nPlease contact the customer to confirm details.',
            'contact': 'Inquiry from contact form\n\nPlease respond to the inquiry.',
        }
        return descriptions.get(source_type, 'Registered from the website')

    @api.model
    def create_course_lead(self, name, phone, email=None, course_name=None, branch=None):
        """Create lead from course registration."""
        self = self.sudo()

        vals = {
            'name': name,
            'contact_name': name,
            'phone': phone,
            'type': 'opportunity',
            'x_source_type': 'course',
            'x_registration_date': fields.Datetime.now(),
            'stage_id': self._get_safe_stage_id('crm.stage_lead1'),
            'user_id': False,
        }

        if email:
            vals['email_from'] = email
        if course_name:
            vals['x_course_interest'] = course_name
        if branch:
            vals['x_preferred_branch'] = branch

        parts = ['Course registration request', '']
        parts.append(f"📚 Course: {course_name or 'Not specified'}")
        if branch:
            parts.append(f"📍 Preferred Branch: {branch}")
        parts.extend(['', '---', 'Please contact the customer to confirm registration details.'])

        vals['description'] = '\n'.join(parts)

        lead = self.create(vals)
        _logger.info(f"Course lead created: ID={lead.id}, Course={course_name}")

        return lead

    # ============================================================
    # ACTIONS
    # ============================================================

    def action_view_popup_offer(self):
        """Open related popup offer."""
        self.ensure_one()
        if not self.x_popup_offer_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'popup.offer',
            'res_id': self.x_popup_offer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }