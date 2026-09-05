# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PopupOffer(models.Model):
    _name = 'popup.offer'
    _description = 'Pop-up Offers'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'
    _rec_name = 'name'

    # ============================================================
    # BASIC INFORMATION
    # ============================================================

    name = fields.Char(
        string='Offer Name',
        required=True,
        help='Internal offer name (e.g., Ramadan Offer 2026)'
    )

    # ✅ إضافة name_en للدعم الثنائي اللغة
    name_en = fields.Char(
        string='Offer Name (English)',
        help='Internal offer name in English'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Offer priority (lower number = higher priority)'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Deactivating stops the offer immediately'
    )

    # ============================================================
    # OFFER TYPE & SETTINGS
    # ============================================================

    offer_type = fields.Selection([
        ('buy_x_get_y', 'Buy X Get Y Free'),
        ('discount_percentage', 'Percentage Discount'),
        ('discount_fixed', 'Fixed Amount Discount'),
        ('free_consultation', 'Free Consultation'),
        ('custom', 'Custom Offer'),
    ], string='Offer Type', required=True, default='buy_x_get_y',
        help='Offer type determines how it is displayed in the Pop-up')

    # Buy X Get Y Settings
    buy_quantity = fields.Integer(
        string='Courses to Buy',
        default=2,
        help='Number of courses that must be purchased'
    )

    get_quantity = fields.Integer(
        string='Free Courses',
        default=1,
        help='Number of free courses'
    )

    # Discount Settings
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Type', default='percentage')

    discount_value = fields.Float(
        string='Discount Value',
        help='Percentage or fixed amount'
    )

    # ============================================================
    # DISPLAY CONTENT (Arabic & English)
    # ============================================================

    title_ar = fields.Char(
        string='Title (Arabic)',
        required=True,
        help='Main offer title in Arabic'
    )

    title_en = fields.Char(
        string='Title (English)',
        help='Main offer title in English'
    )

    subtitle_ar = fields.Char(
        string='Subtitle (Arabic)',
        help='Additional text below the title'
    )

    subtitle_en = fields.Char(
        string='Subtitle (English)'
    )

    description_ar = fields.Text(
        string='Description (Arabic)',
        help='Detailed offer description'
    )

    description_en = fields.Text(
        string='Description (English)'
    )

    # ============================================================
    # BADGE CUSTOMIZATION
    # ============================================================

    badge_text_ar = fields.Char(
        string='Badge Text (Arabic)',
        default='عرض لفترة محدودة!',
        help='Text displayed on the offer badge in Arabic'
    )

    badge_text_en = fields.Char(
        string='Badge Text (English)',
        default='Limited Time Offer!',
        help='Text displayed on the offer badge in English'
    )

    badge_text = fields.Char(
        string='Badge Text',
        compute='_compute_badge_text',
        store=False
    )

    badge_color = fields.Char(
        string='Badge Color',
        default='#ff6b6b',
        help='Hex color code (e.g., #ff6b6b)'
    )

    @api.depends('badge_text_ar')
    def _compute_badge_text(self):
        for record in self:
            record.badge_text = record.badge_text_ar

    # ============================================================
    # DATES & SCHEDULING
    # ============================================================

    start_date = fields.Datetime(
        string='Start Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help='Offer start date and time'
    )

    end_date = fields.Datetime(
        string='End Date',
        tracking=True,
        help='Offer end date and time (leave empty for unlimited offers)'
    )

    # ============================================================
    # COUNTDOWN TIMER
    # ============================================================

    show_countdown = fields.Boolean(
        string='Show Countdown',
        default=True,
        help='Display countdown timer in Pop-up'
    )

    countdown_days = fields.Integer(
        string='Countdown Days',
        compute='_compute_countdown_days',
        store=True,
        help='Days remaining (calculated automatically)'
    )

    # ============================================================
    # TERMS & CONDITIONS
    # ============================================================

    terms_ar = fields.Text(
        string='Terms & Conditions (Arabic)',
        help='Offer terms and conditions'
    )

    terms_en = fields.Text(
        string='Terms & Conditions (English)'
    )

    # ============================================================
    # POP-UP BEHAVIOR SETTINGS
    # ============================================================

    delay_seconds = fields.Integer(
        string='Delay (Seconds)',
        default=3,
        help='Seconds to wait before showing Pop-up'
    )

    cookie_duration = fields.Integer(
        string='Cookie Duration (Days)',
        default=7,
        help='Days before showing Pop-up again to same visitor'
    )

    exit_intent = fields.Boolean(
        string='Show on Exit Intent',
        default=False,
        help='Show Pop-up when user tries to leave the page'
    )

    # ============================================================
    # STATIC TEXT CUSTOMIZATION (Arabic & English)
    # ============================================================

    form_title_ar = fields.Char(
        string='Form Title (Arabic)',
        default='سجّل الآن واحجز مقعدك!',
    )
    form_title_en = fields.Char(
        string='Form Title (English)',
        default='Register Now and Reserve Your Spot!',
    )

    form_subtitle_ar = fields.Char(
        string='Form Subtitle (Arabic)',
        default='أدخل بياناتك وسيتواصل معك فريقنا خلال 24 ساعة لتأكيد العرض',
    )
    form_subtitle_en = fields.Char(
        string='Form Subtitle (English)',
        default='Enter your details and our team will contact you within 24 hours to confirm the offer',
    )

    name_label_ar = fields.Char(default='الاسم الكامل')
    name_label_en = fields.Char(default='Full Name')
    name_placeholder_ar = fields.Char(default='مثال: أحمد محمد')
    name_placeholder_en = fields.Char(default='e.g., John Smith')

    phone_label_ar = fields.Char(default='رقم الهاتف')
    phone_label_en = fields.Char(default='Phone Number')
    phone_placeholder_ar = fields.Char(default='05XXXXXXXX')
    phone_placeholder_en = fields.Char(default='05XXXXXXXX')

    submit_btn_ar = fields.Char(default='احصل على العرض الآن')
    submit_btn_en = fields.Char(default='Get the Offer Now')
    close_btn_ar = fields.Char(default='ربما لاحقاً')
    close_btn_en = fields.Char(default='Maybe Later')

    success_title_ar = fields.Char(default='مبروك! تم حجز العرض بنجاح 🎉')
    success_title_en = fields.Char(default='Congratulations! Offer Reserved Successfully 🎉')
    success_message_ar = fields.Text(
        default='شكراً لك {name}! سيتواصل معك فريقنا خلال 24 ساعة لتأكيد حجزك والاستفادة من العرض.'
    )
    success_message_en = fields.Text(
        default='Thank you {name}! Our team will contact you within 24 hours to confirm your reservation.'
    )

    social_proof_ar = fields.Char(default='انضم لأكثر من 10,000+ متدرب استفادوا من عروضنا!')
    social_proof_en = fields.Char(default='Join 10,000+ trainees who benefited from our offers!')

    trust_text_ar = fields.Char(default='معلوماتك آمنة ومحمية | لن نشارك بياناتك مع أي طرف ثالث')
    trust_text_en = fields.Char(
        default='Your Information is Safe and Protected | We will not share your data with any third party')

    countdown_title_ar = fields.Char(default='ينتهي العرض خلال:')
    countdown_title_en = fields.Char(default='Offer Ends In:')
    days_label_ar = fields.Char(default='يوم')
    days_label_en = fields.Char(default='Days')
    hours_label_ar = fields.Char(default='ساعة')
    hours_label_en = fields.Char(default='Hours')
    mins_label_ar = fields.Char(default='دقيقة')
    mins_label_en = fields.Char(default='Minutes')

    # ============================================================
    # ANALYTICS & TRACKING
    # ============================================================

    view_count = fields.Integer(
        string='View Count',
        readonly=True,
        default=0,
        help='Number of times Pop-up was displayed'
    )

    lead_count = fields.Integer(
        string='Lead Count',
        compute='_compute_lead_count',
        help='Number of Leads from this offer'
    )

    conversion_rate = fields.Float(
        string='Conversion Rate %',
        compute='_compute_conversion_rate',
        digits=(5, 2),
        help='Percentage of views converted to leads'
    )

    # ============================================================
    # STATE & STATUS
    # ============================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('paused', 'Paused'),
    ], string='Status', compute='_compute_state', store=True, tracking=True,
        help='Offer status (calculated automatically)')

    # ============================================================
    # RELATIONS
    # ============================================================

    # ✅ تم تغيير الـ One2many لتكون computed بدلاً من inverse
    # هذا يحل مشكلة ترتيب التحميل
    lead_ids = fields.One2many(
        'crm.lead',
        'x_popup_offer_id',
        string='Registrations',
        help='All Leads from this offer'
    )

    # ============================================================
    # COMPUTED FIELDS
    # ============================================================

    @api.depends('start_date', 'end_date', 'active')
    def _compute_state(self):
        """Calculate offer status automatically based on date and activation"""
        now = fields.Datetime.now()

        for offer in self:
            if not offer.active:
                offer.state = 'paused'
            elif not offer.start_date:
                offer.state = 'draft'
            elif offer.start_date > now:
                offer.state = 'scheduled'
            elif offer.end_date and offer.end_date < now:
                offer.state = 'expired'
            else:
                offer.state = 'active'

    @api.depends('end_date')
    def _compute_countdown_days(self):
        """Calculate remaining days for the offer"""
        now = fields.Datetime.now()

        for offer in self:
            if offer.end_date:
                delta = offer.end_date - now
                offer.countdown_days = max(0, delta.days)
            else:
                offer.countdown_days = 0

    def _compute_lead_count(self):
        """Calculate number of registrations from this offer"""
        for offer in self:
            offer.lead_count = self.env['crm.lead'].sudo().search_count([
                ('x_popup_offer_id', '=', offer.id)
            ])

    def _compute_conversion_rate(self):
        """Calculate conversion rate from views to registrations"""
        for offer in self:
            if offer.view_count > 0:
                offer.conversion_rate = (offer.lead_count / offer.view_count) * 100
            else:
                offer.conversion_rate = 0.0

    # ============================================================
    # BUSINESS METHODS
    # ============================================================

    @api.model
    def get_active_offer(self):
        """Get the current active offer"""
        now = fields.Datetime.now()

        offer = self.search([
            ('active', '=', True),
            ('start_date', '<=', now),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', now),
        ], order='sequence, id desc', limit=1)

        if offer:
            offer.sudo().write({'view_count': offer.view_count + 1})

        return offer

    def increment_view(self):
        """Increment view count"""
        self.ensure_one()
        self.sudo().write({'view_count': self.view_count + 1})

    def get_offer_data_localized(self, is_english=False):
        """Get offer data in JSON format with localized content"""
        self.ensure_one()

        lang = 'en' if is_english else 'ar'

        if self.offer_type == 'buy_x_get_y':
            if is_english:
                offer_highlight = f'Buy {self.buy_quantity} Get {self.get_quantity} FREE'
                submit_text = f'Get Offer - Buy {self.buy_quantity} Get {self.get_quantity} Free!'
            else:
                offer_highlight = f'اشترِ {self.buy_quantity} واحصل على {self.get_quantity} مجاناً'
                submit_text = f'احصل على العرض - اشترِ {self.buy_quantity} واحصل على {self.get_quantity} مجاناً!'
        elif self.offer_type == 'discount_percentage':
            offer_highlight = f'{int(self.discount_value)}% OFF' if is_english else f'خصم {int(self.discount_value)}%'
            submit_text = f'Get {int(self.discount_value)}% Discount Now!' if is_english else f'احصل على خصم {int(self.discount_value)}% الآن!'
        elif self.offer_type == 'discount_fixed':
            offer_highlight = f'AED {int(self.discount_value)} OFF' if is_english else f'خصم {int(self.discount_value)} درهم'
            submit_text = f'Save AED {int(self.discount_value)} Now!' if is_english else f'وفّر {int(self.discount_value)} درهم الآن!'
        elif self.offer_type == 'free_consultation':
            offer_highlight = 'Free Consultation' if is_english else 'استشارة مجانية'
            submit_text = 'Book Free Consultation!' if is_english else 'احجز استشارتك المجانية!'
        else:
            offer_highlight = getattr(self, f'title_{lang}') or self.title_ar
            submit_text = getattr(self, f'submit_btn_{lang}') or self.submit_btn_ar

        return {
            'id': self.id,
            'name': self.name,
            'offer_type': self.offer_type,
            'title': getattr(self, f'title_{lang}') or self.title_ar,
            'subtitle': getattr(self, f'subtitle_{lang}') or self.subtitle_ar or '',
            'description': getattr(self, f'description_{lang}') or self.description_ar or '',
            'badge_text': getattr(self, f'badge_text_{lang}') or self.badge_text_ar,
            'badge_color': self.badge_color,
            'show_countdown': self.show_countdown,
            'countdown_days': self.countdown_days,
            'countdown_title': getattr(self, f'countdown_title_{lang}'),
            'days_label': getattr(self, f'days_label_{lang}'),
            'hours_label': getattr(self, f'hours_label_{lang}'),
            'mins_label': getattr(self, f'mins_label_{lang}'),
            'terms': getattr(self, f'terms_{lang}') or self.terms_ar or '',
            'form_title': getattr(self, f'form_title_{lang}'),
            'form_subtitle': getattr(self, f'form_subtitle_{lang}'),
            'name_label': getattr(self, f'name_label_{lang}'),
            'name_placeholder': getattr(self, f'name_placeholder_{lang}'),
            'phone_label': getattr(self, f'phone_label_{lang}'),
            'phone_placeholder': getattr(self, f'phone_placeholder_{lang}'),
            'submit_btn_text': submit_text,
            'close_btn_text': getattr(self, f'close_btn_{lang}'),
            'success_title': getattr(self, f'success_title_{lang}'),
            'success_message': getattr(self, f'success_message_{lang}'),
            'social_proof': getattr(self, f'social_proof_{lang}'),
            'trust_text': getattr(self, f'trust_text_{lang}'),
            'offer_highlight': offer_highlight,
            'buy_quantity': self.buy_quantity,
            'get_quantity': self.get_quantity,
            'discount_value': self.discount_value,
            'delay_seconds': self.delay_seconds,
            'cookie_duration': self.cookie_duration,
            'exit_intent': self.exit_intent,
        }

    def get_offer_data(self):
        """Legacy method - returns Arabic content by default"""
        return self.get_offer_data_localized(is_english=False)

    def action_view_leads(self):
        """Open list of Leads from this offer"""
        self.ensure_one()
        return {
            'name': f'Registrations: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('x_popup_offer_id', '=', self.id)],
            'context': {
                'default_x_popup_offer_id': self.id,
                'default_x_source_type': 'popup',
            },
        }

    # ============================================================
    # CONSTRAINTS & VALIDATIONS
    # ============================================================

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate dates"""
        for offer in self:
            if offer.end_date and offer.start_date:
                if offer.end_date < offer.start_date:
                    raise models.ValidationError(
                        _('End date must be after start date!')
                    )

    @api.constrains('delay_seconds')
    def _check_delay(self):
        """Validate delay value"""
        for offer in self:
            if offer.delay_seconds < 0:
                raise models.ValidationError(
                    _('Delay cannot be negative!')
                )

    @api.constrains('cookie_duration')
    def _check_cookie_duration(self):
        """Validate cookie duration"""
        for offer in self:
            if offer.cookie_duration < 1:
                raise models.ValidationError(
                    _('Cookie duration must be at least 1 day!')
                )