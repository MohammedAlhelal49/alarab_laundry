# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class AlomranWebsite(http.Controller):

    def _get_current_lang(self):
        """Get current language code"""
        lang = request.env.lang or request.httprequest.cookies.get('frontend_lang') or 'ar_001'
        return lang

    def _is_english(self):
        """Check if current language is English"""
        return self._get_current_lang().startswith('en')

    # ============================================================
    # HELPER METHODS FOR POPUP
    # ============================================================

    def _clean_phone(self, phone):
        """Clean phone number from spaces and special characters"""
        if not phone:
            return ''
        return ''.join(filter(str.isdigit, phone.replace('+', '')))

    def _validate_phone(self, phone):
        """Validate phone number format"""
        if not phone:
            return False
        cleaned = self._clean_phone(phone)
        return len(cleaned) >= 9 and len(cleaned) <= 15

    def _is_duplicate_submission(self, phone, offer_id):
        """Check if same phone submitted in last 24 hours"""
        try:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(hours=24)

            domain = [
                ('phone', '=', phone),
                ('create_date', '>=', yesterday.strftime('%Y-%m-%d %H:%M:%S')),
            ]

            if offer_id and 'x_popup_offer_id' in request.env['crm.lead']._fields:
                domain.append(('x_popup_offer_id', '=', int(offer_id)))

            existing = request.env['crm.lead'].sudo().search_count(domain)
            return existing > 0
        except Exception as e:
            _logger.warning(f"Error checking duplicate: {e}")
            return False

    def _get_error_message(self, error_type):
        """Get localized error message"""
        is_en = self._is_english()
        messages = {
            'name_required': 'Please enter your name' if is_en else 'الرجاء إدخال اسمك',
            'phone_required': 'Please enter your phone number' if is_en else 'الرجاء إدخال رقم الهاتف',
            'phone_invalid': 'Please enter a valid phone number' if is_en else 'الرجاء إدخال رقم هاتف صحيح',
            'duplicate': 'You have already registered for this offer' if is_en else 'لقد سجلت مسبقاً في هذا العرض',
            'general': 'An error occurred, please try again' if is_en else 'حدث خطأ، يرجى المحاولة مرة أخرى',
        }
        return messages.get(error_type, messages['general'])

    def _get_success_message(self, is_english):
        """Get localized success message"""
        if is_english:
            return 'Thank you for registering! We will contact you soon.'
        return 'شكراً لتسجيلك! سنتواصل معك قريباً.'

    def _build_lead_description(self, offer, is_english):
        """Build lead description"""
        if not offer:
            return 'Popup registration' if is_english else 'تسجيل من النافذة المنبثقة'

        offer_name = getattr(offer, 'name_en', None) if is_english else None
        if not offer_name:
            offer_name = getattr(offer, 'name', 'Offer')
        return f"{'Popup Offer' if is_english else 'عرض النافذة المنبثقة'}: {offer_name}"

    def _get_or_create_utm_source(self, source_name):
        """Get or create UTM source"""
        try:
            utm_source = request.env['utm.source'].sudo().search([('name', '=', source_name)], limit=1)
            if not utm_source:
                utm_source = request.env['utm.source'].sudo().create({'name': source_name})
            return utm_source.id
        except Exception as e:
            _logger.warning(f"Error with UTM source: {e}")
            return False

    def _is_valid_selection_value(self, model_name, field_name, value):
        """Check if a value is valid for a selection field"""
        try:
            field = request.env[model_name]._fields.get(field_name)
            if not field:
                return False
            if field.type != 'selection':
                return True
            if callable(field.selection):
                selection_values = [s[0] for s in field.selection(request.env[model_name])]
            else:
                selection_values = [s[0] for s in field.selection]
            return value in selection_values
        except Exception as e:
            _logger.warning(f"Error checking selection value: {e}")
            return False

    def _safe_set_field(self, vals, model_name, field_name, value):
        """Safely set a field value only if it's valid"""
        try:
            if field_name not in request.env[model_name]._fields:
                _logger.debug(f"Field {field_name} not found in {model_name}")
                return False
            field = request.env[model_name]._fields[field_name]
            if field.type == 'selection':
                if not self._is_valid_selection_value(model_name, field_name, value):
                    _logger.warning(f"Invalid selection value '{value}' for {model_name}.{field_name}")
                    return False
            vals[field_name] = value
            return True
        except Exception as e:
            _logger.warning(f"Error setting field {field_name}: {e}")
            return False

    # ============================================================
    # MAIN PAGES
    # ============================================================

    @http.route('/', type='http', auth='public', website=True)
    def homepage(self, **kwargs):
        """Homepage"""
        is_en = self._is_english()

        stats = [
            {'icon': 'fa-user-graduate', 'number': '10,000+', 'label': 'Active Trainees' if is_en else 'متدرب نشط'},
            {'icon': 'fa-building', 'number': '50+', 'label': 'Government Entities' if is_en else 'جهة حكومية'},
            {'icon': 'fa-chalkboard-teacher', 'number': '50+', 'label': 'Expert Trainers' if is_en else 'مدرب متخصص'},
            {'icon': 'fa-certificate', 'number': '100+', 'label': 'Training Programs' if is_en else 'برنامج تدريبي'},
        ]

        return request.render('alomran_theme.homepage', {'stats': stats})

    @http.route('/about', type='http', auth='public', website=True)
    def about(self, **kwargs):
        """About Us page"""
        is_en = self._is_english()

        values = [
            {'icon': 'fa-award', 'title': 'Excellence' if is_en else 'التميز',
             'description': 'We always strive to provide the best training services' if is_en else 'نسعى دائماً لتقديم أفضل الخدمات التدريبية'},
            {'icon': 'fa-shield-alt', 'title': 'Credibility' if is_en else 'المصداقية',
             'description': 'We adhere to the highest standards of transparency and integrity' if is_en else 'نلتزم بأعلى معايير الشفافية والنزاهة'},
            {'icon': 'fa-lightbulb', 'title': 'Innovation' if is_en else 'الابتكار',
             'description': 'We develop modern and innovative training methods' if is_en else 'نطور أساليب تدريبية حديثة ومبتكرة'},
            {'icon': 'fa-handshake', 'title': 'Collaboration' if is_en else 'التعاون',
             'description': 'We build strong partnerships with our clients' if is_en else 'نبني شراكات قوية مع عملائنا'},
            {'icon': 'fa-chart-line', 'title': 'Continuous Development' if is_en else 'التطوير المستمر',
             'description': 'We constantly update our programs to keep up with the market' if is_en else 'نحدث برامجنا باستمرار لمواكبة السوق'},
            {'icon': 'fa-heart', 'title': 'Customer Care' if is_en else 'الاهتمام بالعميل',
             'description': 'We prioritize customer satisfaction' if is_en else 'نضع رضا العميل في المقام الأول'},
        ]

        return request.render('alomran_theme.about_template', {'values': values})

    @http.route('/courses', type='http', auth='public', website=True)
    def courses(self, **kwargs):
        """Courses page"""
        is_en = self._is_english()

        courses = [
            {
                'icon': 'fa-graduation-cap',
                'badge': 'Most Requested' if is_en else 'الأكثر طلباً',
                'badge_class': 'bg-primary',
                'title': 'Professional Teacher Training' if is_en else 'تأهيل المعلمين المحترف',
                'description': 'Specialized programs for developing educational competencies and modern pedagogical skills' if is_en else 'برامج متخصصة لتطوير الكفاءات التعليمية والمهارات التربوية الحديثة',
                'students': '2,500+',
                'hours': '120',
                'link': '/teachers',
                'button_text': 'View More' if is_en else 'عرض المزيد',
            },
            {
                'icon': 'fa-language',
                'badge': 'New' if is_en else 'جديد',
                'badge_class': 'bg-success',
                'title': 'Language Learning' if is_en else 'تعلم اللغات',
                'description': 'Comprehensive courses in English, French, German, Chinese and more' if is_en else 'دورات شاملة في الإنجليزية والفرنسية والألمانية والصينية وغيرها',
                'students': '3,200+',
                'hours': '80',
                'link': '/languages',
                'button_text': 'View More' if is_en else 'عرض المزيد',
            },
            {
                'icon': 'fa-laptop-code',
                'badge': 'Featured' if is_en else 'مميز',
                'badge_class': 'bg-warning',
                'title': 'Information Technology' if is_en else 'تقنية المعلومات',
                'description': 'Programming, graphic design, cybersecurity, and data science' if is_en else 'البرمجة والتصميم الجرافيكي والأمن السيبراني وعلوم البيانات',
                'students': '1,800+',
                'hours': '160',
                'link': '/it-programs',
                'button_text': 'View More' if is_en else 'عرض المزيد',
            },
            {
                'icon': 'fa-cut',
                'badge': 'Practical' if is_en else 'عملي',
                'badge_class': 'bg-info',
                'title': 'Fashion & Design' if is_en else 'الأزياء والتصميم',
                'description': 'Fashion design, sewing, and professional tailoring' if is_en else 'تعلم تصميم الأزياء وتصميم العبايات والفساتين، مع دورات قص وخياطة احترافية',
                'students': '950+',
                'hours': '90',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-spa',
                'badge': 'Professional' if is_en else 'احترافي',
                'badge_class': 'bg-primary',
                'title': 'Skincare' if is_en else 'العناية بالبشرة',
                'description': 'Specialized courses in skincare and natural beauty' if is_en else 'دورات متخصصة في العناية بالبشرة والجمال الطبيعي',
                'students': '1,100+',
                'hours': '70',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-balance-scale',
                'badge': 'Advanced' if is_en else 'متقدم',
                'badge_class': 'bg-danger',
                'title': 'Law' if is_en else 'القانون',
                'description': 'Qualifying courses in law and legal procedures' if is_en else 'دورات تأهيلية في القانون والإجراءات القانونية',
                'students': '650+',
                'hours': '140',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-file-alt',
                'badge': 'Professional' if is_en else 'احترافي',
                'badge_class': 'bg-success',
                'title': 'Secretarial' if is_en else 'السكرتارية',
                'description': 'Office management, executive secretarial, and communication skills' if is_en else 'إدارة المكاتب والسكرتارية التنفيذية ومهارات التواصل',
                'students': '1,400+',
                'hours': '60',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-calculator',
                'badge': 'Accredited' if is_en else 'معتمد',
                'badge_class': 'bg-primary',
                'title': 'Accounting' if is_en else 'المحاسبة',
                'description': 'Financial accounting, management accounting, and banking sciences' if is_en else 'المحاسبة المالية والإدارية والعلوم المصرفية',
                'students': '1,650+',
                'hours': '110',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-bullhorn',
                'badge': 'Modern' if is_en else 'حديث',
                'badge_class': 'bg-warning',
                'title': 'Marketing' if is_en else 'التسويق',
                'description': 'Digital marketing, brand management, and social media' if is_en else 'التسويق الرقمي وإدارة العلامات التجارية ووسائل التواصل الاجتماعي',
                'students': '2,100+',
                'hours': '95',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-users-cog',
                'badge': 'Strategic' if is_en else 'استراتيجي',
                'badge_class': 'bg-info',
                'title': 'Human Resources' if is_en else 'الموارد البشرية',
                'description': 'HR management, recruitment, and career development' if is_en else 'إدارة الموارد البشرية والتوظيف والتطوير المهني',
                'students': '1,750+',
                'hours': '105',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-video',
                'badge': 'Creative' if is_en else 'إبداعي',
                'badge_class': 'bg-danger',
                'title': 'Media & Editing' if is_en else 'الإعلام والمونتاج',
                'description': 'Content production, video editing, and filmmaking' if is_en else 'إنتاج المحتوى وتحرير الفيديو وصناعة الأفلام',
                'students': '890+',
                'hours': '130',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
            {
                'icon': 'fa-briefcase',
                'badge': 'Leadership' if is_en else 'قيادي',
                'badge_class': 'bg-primary',
                'title': 'Business Administration' if is_en else 'إدارة الأعمال',
                'description': 'Leadership skills, project management, and decision making' if is_en else 'مهارات القيادة وإدارة المشاريع واتخاذ القرارات',
                'students': '2,100+',
                'hours': '100',
                'link': '#register',
                'button_text': 'Register Now' if is_en else 'سجل الآن',
                'register_direct': True,
            },
        ]

        return request.render('alomran_theme.courses_template', {'courses': courses})

    def _get_branches_data(self, is_en):
        """Get all branches data - centralized for reuse"""
        return [
            {
                'slug': 'sharjah-central-mall',
                'name': 'Sharjah Branch | Central Mall' if is_en else 'فرع الشارقة | سنترال مول',
                'city': 'Sharjah' if is_en else 'الشارقة',
                'badge_class': 'bg-warning',
                'location': 'Sharjah - Central Mall - First floor' if is_en else 'الشارقة - سنترال مول - طـ 1',
                'phone': '+971 56 414 1409',
                'phone_link': '971564141409',
                'maps_link': 'https://maps.app.goo.gl/SqjyxrKBsU5LsyPN6',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1846252.4627421533!2d57.85537719726561!3d25.3390614588184!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e5f5987a4caac77%3A0xb875acbf965eb114!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INin2YTYtNin2LHZgtip!5e0!3m2!1sar!2slt!4v1771378619575!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/sharjah_center.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'alain-city-center',
                'name': 'Al Ain Branch | City Center' if is_en else 'فرع العين | سيتي سنتر',
                'city': 'Al Ain' if is_en else 'العين',
                'badge_class': 'bg-primary',
                'location': 'Al Ain - City Center - Murbaa' if is_en else 'العين - سيتي سنتر - المربعة',
                'phone': '+971 56 434 2889',
                'phone_link': '971505829697',
                'maps_link': 'https://maps.app.goo.gl/CATYSRrQgXAEVbqy9',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1862946.6091659945!2d58.21243286132814!3d24.221919199872975!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e8ab78bb01d0847%3A0x402d1b2a947d37f1!2sAl%20Omran%20center%20for%20training%20and%20developing!5e0!3m2!1sar!2slt!4v1771377608099!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/alain_murbaa.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'alain-foah-mall',
                'name': 'Al Ain Branch | Al Foah Mall' if is_en else 'فرع العين | الفوعة مول',
                'city': 'Al Ain' if is_en else 'العين',
                'badge_class': 'bg-primary',
                'location': 'Al Ain - Al Foah Mall' if is_en else 'العين - الفوعة مول',
                'phone': '+971 56 573 3506',
                'phone_link': '971565733506',
                'maps_link': 'https://maps.app.goo.gl/zzUzT5iS8wZXjAVc7',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1861166.29000234!2d58.23165893554686!3d24.343343107244273!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3ef54b16a9464c27%3A0x7c74d0bf4c530123!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INin2YTZgdmI2LnYqQ!5e0!3m2!1sar!2slt!4v1771377722255!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/alain_alfouaa.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'alain-barari-mall',
                'name': 'Al Ain Branch | Al Barari Mall' if is_en else 'فرع العين | البراري مول',
                'city': 'Al Ain' if is_en else 'العين',
                'badge_class': 'bg-primary',
                'location': 'Al Ain - Al Barari Mall' if is_en else 'العين - البراري مول',
                'phone': '+971 56 635 9986',
                'phone_link': '971566359986',
                'maps_link': 'https://maps.app.goo.gl/cxZwAUdZvCV33dnHA',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3642.4396765191404!2d55.8298772!3d24.086028799999998!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e8abf002a3c24e3%3A0x612b51ca0e6fedca!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INin2YTZiNix2KfYqiDZhdmI2YQ!5e0!3m2!1sar!2slt!4v1771377222330!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/alain_albrari.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'alain-yahar-mall',
                'name': 'Al Ain Branch | Al Yahar Mall' if is_en else 'فرع العين | الياهر مول',
                'city': 'Al Ain' if is_en else 'العين',
                'badge_class': 'bg-primary',
                'location': 'Al Ain - Al Yahar Mall' if is_en else 'العين - الياهر مول',
                'phone': '+971 54 247 6015',
                'phone_link': '971542476015',
                'maps_link': 'https://maps.app.goo.gl/wvRP9zkHkaLgHXuk8',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1862964.9282502981!2d57.98171997070311!3d24.220666802807237!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e8aab1b21a70995%3A0x8b4e507f5a233cac!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INin2YTYudin2YXYsdip!5e0!3m2!1sar!2slt!4v1771377929835!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/allain_alyaher.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'zakher-makani-mall',
                'name': 'Zakher Branch | Makani Mall' if is_en else 'فرع زاخر | مكاني مول',
                'city': 'Al Ain' if is_en else 'العين',
                'badge_class': 'bg-primary',
                'location': 'Zakher - Makani Mall' if is_en else 'زاخر - مكاني مول',
                'phone': '+971 56 434 2889',
                'phone_link': '971505829697',
                'maps_link': 'https://maps.app.goo.gl/x52eSzwpa7HPwbrbA',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1864592.4783181893!2d58.14102172851561!3d24.10915419847753!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e8abbbcfe88aafb%3A0x6f60a31b074fad23!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INmF2YPYp9mG2Yog2YXZiNmEINiy2KfYrtix!5e0!3m2!1sar!2slt!4v1771377839762!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/alain_zakher.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'abudhabi-mazyed-mall',
                'name': 'Abu Dhabi Branch | Mazyed Mall' if is_en else 'فرع أبوظبي | مزيد مول',
                'city': 'Abu Dhabi' if is_en else 'أبوظبي',
                'badge_class': 'bg-success',
                'location': 'Abu Dhabi - Mazyed Mall - Second floor' if is_en else 'أبوظبي - مزيد مول - طـ 2',
                'phone': '+971 56 659 9919',
                'phone_link': '971566599919',
                'maps_link': 'https://maps.app.goo.gl/2TZ819WHstLZwZXx7',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d232588.58344729056!2d54.845294952392585!3d24.374462733901805!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e5e4723b6b3e2ed%3A0x68af7c666c2da83c!2z2LTYp9ix2Lkg2LPZhNi32KfZhiDYqNmGINmF2K3ZhdivINin2YTZgtio2YrYs9mKIC8g2YXYstmK2K8g2YXZiNmE!5e0!3m2!1sar!2slt!4v1771378027540!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/abudhabi_mazyd.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'abudhabi-muroor',
                'name': 'Abu Dhabi Branch | Al Muroor' if is_en else 'فرع أبوظبي | المرور',
                'city': 'Abu Dhabi' if is_en else 'أبوظبي',
                'badge_class': 'bg-success',
                'location': 'Abu Dhabi - Al Muroor Street' if is_en else 'أبوظبي - شارع المرور',
                'phone': '+971 50 172 0927',
                'phone_link': '971501720927',
                'maps_link': 'https://maps.app.goo.gl/nezYWL2BYTEUHvbf9',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d3631.2847310108154!2d54.3762301850047!3d24.475589484236885!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e5e67006bbe0b5f%3A0x97b4ffaefcae532a!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INin2KjZiNi42KjZiiDYtNin2LHYuSDYp9mE2YXYsdmI2LE!5e0!3m2!1sar!2slt!4v1771378199267!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/abudabi_almoror.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'dubai-garhoud',
                'name': 'Dubai Branch | Al Garhoud' if is_en else 'فرع دبي | القرهود',
                'city': 'Dubai' if is_en else 'دبي',
                'badge_class': 'bg-info',
                'location': 'Dubai - Al Garhoud' if is_en else 'دبي - القرهود',
                'phone': '+971 50 559 5228',
                'phone_link': '971505595228',
                'maps_link': 'https://maps.app.goo.gl/KPe6jwVUEFZJ9fKTA',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d923783.5359432719!2d56.56105041503905!3d25.252769556326484!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e5f5dcc0638abf3%3A0xf7abd5f5920bdc28!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INiv2KjZiiDYp9mE2YLYsdmH2YjYrw!5e0!3m2!1sar!2slt!4v1771378338236!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/dubai_alkarhod.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'dubai-barsha',
                'name': 'Dubai Branch | Al Barsha' if is_en else 'فرع دبي | البرشاء',
                'city': 'Dubai' if is_en else 'دبي',
                'badge_class': 'bg-info',
                'location': 'Dubai - Al Barsha' if is_en else 'دبي - البرشاء',
                'phone': '+971 50 610 8091',
                'phone_link': '971506108091',
                'maps_link': 'https://maps.app.goo.gl/f6kEvPw7FzKpSu3H8',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3612.7991416704585!2d55.184069699999995!3d25.1086597!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e5f6bd7b2fe688d%3A0xbb00ef3993ecffcb!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INi02KfYsdi5INin2YTYtNmK2K4g2LLYp9mK2K8g2K_YqNmK!5e0!3m2!1sar!2slt!4v1771378453145!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/dubai_albarshaa.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
            {
                'slug': 'rak-rak-mall',
                'name': 'Ras Al Khaimah Branch | RAK Mall' if is_en else 'فرع رأس الخيمة | راك مول',
                'city': 'Ras Al Khaimah' if is_en else 'رأس الخيمة',
                'badge_class': 'bg-danger',
                'location': 'Ras Al Khaimah - RAK Mall' if is_en else 'رأس الخيمة - راك مول',
                'phone': '+971 52 862 0601',
                'phone_link': '971528620601',
                'maps_link': 'https://maps.app.goo.gl/pV2LmsL4NZCxzcrc9',
                'embed_link': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3592.9505634965103!2d55.95852920000001!3d25.772196399999995!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3ef677f73614a557%3A0x85e8e4499d907f54!2z2YXYsdmD2LIg2KfZhNi52YXYsdin2YYg2YTZhNiq2K_YsdmK2Kgg2Ygg2KfZhNiq2LfZiNmK2LEg2YHYsdi5INix2KPYsyDYp9mE2K7ZitmF2Kk!5e0!3m2!1sar!2slt!4v1771378535800!5m2!1sar!2slt',
                'image': '/alomran_theme/static/src/img/branches/rasalkhima_rakmall.jpg',
                'working_hours': 'Saturday - Thursday: 8:00 AM - 8:00 PM' if is_en else 'السبت - الخميس: 8:00 ص - 8:00 م',
            },
        ]

    @http.route('/branches', type='http', auth='public', website=True)
    def branches(self, **kwargs):
        """Branches page"""
        is_en = self._is_english()
        branches = self._get_branches_data(is_en)
        return request.render('alomran_theme.branches_template', {'branches': branches})

    @http.route('/branch/<string:slug>', type='http', auth='public', website=True)
    def branch_detail(self, slug, **kwargs):
        """Single branch detail page"""
        is_en = self._is_english()
        branches = self._get_branches_data(is_en)

        branch = None
        for b in branches:
            if b.get('slug') == slug:
                branch = b
                break

        if not branch:
            return request.redirect('/branches')

        return request.render('alomran_theme.branch_detail_template', {'branch': branch})

    @http.route('/contact', type='http', auth='public', website=True)
    def contact(self, **kwargs):
        """Contact Us page"""
        return request.render('alomran_theme.custom_contact_template', {})

    @http.route('/contact/submit', type='http', auth='public', methods=['POST'], csrf=True, website=True)
    def contact_submit(self, **post):
        """Process contact form - Stores in CRM + sends email"""
        is_en = self._is_english()

        name = post.get('name', '')
        email = post.get('email_from', '')
        phone = post.get('phone', '')
        subject = post.get('subject', '')
        message = post.get('body_html', '')
        branch = post.get('branch', '')

        # Branch mapping: Real Name (shown to user) -> Odoo Company Name
        BRANCH_MAPPING = {
            'Al Murabba': 'Al Murabba',
            'Mazyad Mall Branch': 'Mazyad Mall Branch',
            'Al Barari Mall Branch': 'Al Barari Mall Branch',
            'Al Foaa Branch': 'Al Foaa Branch',
            'Al Yahr Branch': 'Al Yahr Branch',
            'Al Garhoud Branch (Dubai)': 'Al Garhoud Branch',
            'Zakhir Branch': 'Zakhir Branch',
            'Al Meroor Branch (Abu Dhabi)': 'Al Meroor Branch',
            'Ras Al Khaimah Branch': 'Ras Al Khaimah Branch',
            'Sharjah': 'AL OMRAN EDUCATION LANGUAGES CENTER L.L.C',
            'Fujairah': '-ALOMRAN FOR TRAINING AND DEVELOPING CENTER LLC-',
        }

        try:
            # 1. Create CRM Lead
            lead_values = {
                'name':name,
                'contact_name': name,
                'phone': phone,
                'email_from': email if email else False,
                'description': f"{'Subject' if is_en else 'الموضوع'}: {subject}\n\n{'Branch' if is_en else 'الفرع'}: {branch}\n\n{'Message' if is_en else 'الرسالة'}:\n{message}\n\n{'Source' if is_en else 'المصدر'}: {'Contact Us Page' if is_en else 'صفحة اتصل بنا'}",
                'type': 'opportunity',
            }

            # Get company_id from branch mapping
            company_id = False
            default_salesperson_id = False
            if branch and branch in BRANCH_MAPPING:
                company_name = BRANCH_MAPPING[branch]
                company = request.env['res.company'].sudo().search([('name', '=', company_name)], limit=1)
                if company:
                    company_id = company.id
                    _logger.info(f"Branch '{branch}' mapped to company '{company_name}' (ID: {company.id})")

                    # Find Sales Admin for this company
                    sales_admin_group = request.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
                    if sales_admin_group:
                        admin_user = request.env['res.users'].sudo().search([
                            ('groups_id', 'in', sales_admin_group.id),
                            ('company_ids', 'in', company.id),
                            ('active', '=', True)
                        ], limit=1)
                        if admin_user:
                            default_salesperson_id = admin_user.id
                            _logger.info(
                                f"Default salesperson for '{company_name}': {admin_user.name} (ID: {admin_user.id})")

            lead_values['company_id'] = company_id
            lead_values['user_id'] = default_salesperson_id

            self._safe_set_field(lead_values, 'crm.lead', 'x_source_type', 'contact')
            lead = request.env['crm.lead'].sudo().create(lead_values)
            _logger.info(f"Contact form lead created: {lead.id}")

            # 2. Send email notification
            mail_values = {
                'subject': f'New inquiry from {name} - {subject}' if is_en else f'استفسار جديد من {name} - {subject}',
                'email_from': email,
                'email_to': 'alomran.td@gmail.com',
                'body_html': f"""
                    <h3>{'New inquiry from website' if is_en else 'استفسار جديد من الموقع'}</h3>
                    <p><strong>{'Name' if is_en else 'الاسم'}:</strong> {name}</p>
                    <p><strong>{'Email' if is_en else 'البريد الإلكتروني'}:</strong> {email}</p>
                    <p><strong>{'Phone' if is_en else 'الهاتف'}:</strong> {phone}</p>
                    <p><strong>{'Branch' if is_en else 'الفرع'}:</strong> {branch}</p>
                    <p><strong>{'Subject' if is_en else 'الموضوع'}:</strong> {subject}</p>
                    <p><strong>{'Message' if is_en else 'الرسالة'}:</strong></p>
                    <p>{message}</p>
                    <hr/>
                    <p><small>Lead ID: {lead.id}</small></p>
                """,
            }
            request.env['mail.mail'].sudo().create(mail_values)

            return request.render('alomran_theme.contact_success', {'name': name})

        except Exception as e:
            _logger.error(f'Contact form error: {e}', exc_info=True)
            return request.render('alomran_theme.contact_error', {'error': str(e)})

    # ============================================================
    # POP-UP OFFER ENDPOINTS
    # ============================================================

    @http.route('/popup/settings', type='json', auth='public', website=True)
    def get_popup_settings(self, **kwargs):
        """Get active popup offer settings based on current language"""
        try:
            if 'popup.offer' not in request.env:
                _logger.warning("popup.offer model not found")
                return {'active': False, 'error': 'Model not found'}

            offer = request.env['popup.offer'].sudo().get_active_offer()

            if not offer:
                return {'active': False}

            lang = request.env.lang or request.httprequest.cookies.get('frontend_lang') or 'ar_001'
            is_english = lang.startswith('en')
            is_rtl = lang.startswith('ar') or lang.startswith('he') or lang.startswith('fa')

            _logger.info(f"Popup settings requested - Lang: {lang}, Is English: {is_english}")

            data = offer.get_offer_data_localized(is_english)
            data.update({
                'active': True,
                'current_lang': lang,
                'is_english': is_english,
                'is_rtl': is_rtl,
                'show_on_mobile': True,
            })

            if offer.end_date:
                data['end_timestamp'] = offer.end_date.isoformat()

            return data

        except Exception as e:
            _logger.error(f"Error getting popup settings: {str(e)}", exc_info=True)
            return {'active': False, 'error': str(e)}

    @http.route('/popup/submit', type='json', auth='public', methods=['POST'], website=True)
    def submit_popup_form(self, name=None, phone=None, offer_id=None, **kwargs):
        """Handle popup form submission"""
        try:
            _logger.info(f"Popup submit received - Name: {name}, Phone: {phone}, Offer ID: {offer_id}")

            if not name or not str(name).strip():
                return {'success': False, 'error': self._get_error_message('name_required')}

            if not phone:
                return {'success': False, 'error': self._get_error_message('phone_required')}

            cleaned_phone = self._clean_phone(str(phone))
            if not self._validate_phone(cleaned_phone):
                return {'success': False, 'error': self._get_error_message('phone_invalid')}

            try:
                if self._is_duplicate_submission(cleaned_phone, offer_id):
                    return {'success': False, 'error': self._get_error_message('duplicate')}
            except Exception as e:
                _logger.warning(f"Duplicate check failed: {e}")

            offer = None
            if offer_id:
                try:
                    if 'popup.offer' in request.env:
                        offer = request.env['popup.offer'].sudo().browse(int(offer_id))
                        if not offer.exists():
                            offer = None
                except Exception as e:
                    _logger.warning(f"Error fetching offer: {e}")

            lang = request.env.lang or 'ar_001'
            is_english = lang.startswith('en')

            lead_vals = {
                'name': f"Popup: {str(name).strip()}",
                'contact_name': str(name).strip(),
                'phone': cleaned_phone,
                'description': self._build_lead_description(offer, is_english),
                'type': 'lead',
            }

            self._safe_set_field(lead_vals, 'crm.lead', 'x_source_type', 'popup')

            if offer:
                self._safe_set_field(lead_vals, 'crm.lead', 'x_popup_offer_id', offer.id)

            try:
                utm_source = request.httprequest.cookies.get('utm_source')
                if utm_source:
                    source_id = self._get_or_create_utm_source(utm_source)
                    if source_id:
                        self._safe_set_field(lead_vals, 'crm.lead', 'source_id', source_id)
            except Exception as e:
                _logger.warning(f"UTM source error: {e}")

            _logger.info(f"Creating lead with values: {lead_vals}")
            lead = request.env['crm.lead'].sudo().create(lead_vals)

            _logger.info(f"Popup lead created successfully: {lead.id}")

            return {
                'success': True,
                'lead_id': lead.id,
                'message': self._get_success_message(is_english)
            }

        except Exception as e:
            _logger.error(f"Error submitting popup form: {str(e)}", exc_info=True)
            return {'success': False, 'error': self._get_error_message('general'), 'debug': str(e)}

    # ============================================================
    # TEACHERS PAGE
    # ============================================================

    @http.route('/teachers', type='http', auth='public', website=True)
    def teachers(self, **kwargs):
        """Professional Teacher Training Programs page"""
        return request.render('alomran_theme.teachers_page', {})

    @http.route('/teachers/register', type='json', auth='public', methods=['POST'], website=True)
    def teachers_register(self, **post):
        """Process teacher programs registration"""
        is_en = self._is_english()
        try:
            name = post.get('name', '').strip()
            phone = post.get('phone', '').strip()
            email = post.get('email', '').strip()
            course_name = post.get('course_name', '')

            if not name or not phone:
                return {'success': False, 'error': 'Missing required fields' if is_en else 'الحقول المطلوبة مفقودة'}

            lead_values = {
                'name': name,
                'contact_name': name,
                'phone': phone,
                'email_from': email if email else False,
                'description': f"{'Registration for program' if is_en else 'تسجيل في برنامج'}: {course_name}\n{'Source' if is_en else 'المصدر'}: {'Teachers page' if is_en else 'صفحة المعلمين'}",
                'type': 'opportunity',
            }

            self._safe_set_field(lead_values, 'crm.lead', 'x_source_type', 'course')
            lead = request.env['crm.lead'].sudo().create(lead_values)
            return {'success': True, 'lead_id': lead.id}

        except Exception as e:
            _logger.error(f'Teachers registration error: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    # ============================================================
    # LANGUAGES PAGE
    # ============================================================

    @http.route('/languages', type='http', auth='public', website=True)
    def languages(self, **kwargs):
        """Language Courses page"""
        return request.render('alomran_theme.languages_page', {})

    @http.route('/languages/register', type='json', auth='public', methods=['POST'], website=True)
    def languages_register(self, **post):
        """Process language courses registration"""
        is_en = self._is_english()
        try:
            name = post.get('name', '').strip()
            phone = post.get('phone', '').strip()
            email = post.get('email', '').strip()
            course_name = post.get('course_name', '')

            if not name or not phone:
                return {'success': False, 'error': 'Missing required fields' if is_en else 'الحقول المطلوبة مفقودة'}

            lead_values = {
                'name': name,
                'contact_name': name,
                'phone': phone,
                'email_from': email if email else False,
                'description': f"{'Registration for language course' if is_en else 'تسجيل في دورة لغة'}: {course_name}\n{'Source' if is_en else 'المصدر'}: {'Languages page' if is_en else 'صفحة اللغات'}",
                'type': 'opportunity',
            }

            self._safe_set_field(lead_values, 'crm.lead', 'x_source_type', 'course')
            lead = request.env['crm.lead'].sudo().create(lead_values)
            return {'success': True, 'lead_id': lead.id}

        except Exception as e:
            _logger.error(f'Languages registration error: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    # ============================================================
    # IT PROGRAMS PAGE
    # ============================================================

    @http.route('/it-programs', type='http', auth='public', website=True)
    def it_programs(self, **kwargs):
        """Information Technology Programs page"""
        return request.render('alomran_theme.it_programs_page', {})

    @http.route('/it-programs/register', type='json', auth='public', methods=['POST'], website=True)
    def it_programs_register(self, **post):
        """Process IT programs registration"""
        is_en = self._is_english()
        try:
            name = post.get('name', '').strip()
            phone = post.get('phone', '').strip()
            email = post.get('email', '').strip()
            course_name = post.get('course_name', '')

            if not name or not phone:
                return {'success': False, 'error': 'Missing required fields' if is_en else 'الحقول المطلوبة مفقودة'}

            lead_values = {
                'name': name,
                'contact_name': name,
                'phone': phone,
                'email_from': email if email else False,
                'description': f"{'Registration for IT program' if is_en else 'تسجيل في برنامج تقنية المعلومات'}: {course_name}\n{'Source' if is_en else 'المصدر'}: {'IT Programs page' if is_en else 'صفحة تقنية المعلومات'}",
                'type': 'opportunity',
            }

            self._safe_set_field(lead_values, 'crm.lead', 'x_source_type', 'course')
            lead = request.env['crm.lead'].sudo().create(lead_values)
            return {'success': True, 'lead_id': lead.id}

        except Exception as e:
            _logger.error(f'IT Programs registration error: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    # ============================================================
    # GENERAL COURSE REGISTRATION
    # ============================================================

    @http.route('/course/register', type='json', auth='public', methods=['POST'], website=True)
    def course_register(self, **post):
        """Process general course registration"""
        is_en = self._is_english()
        try:
            name = post.get('name', '').strip()
            phone = post.get('phone', '').strip()
            email = post.get('email', '').strip()
            course_name = post.get('course_name', '')

            if not name or not phone or not course_name:
                return {'success': False, 'error': 'Missing required fields' if is_en else 'الحقول المطلوبة مفقودة'}

            lead_values = {
                'name': name,
                'contact_name': name,
                'phone': phone,
                'email_from': email if email else False,
                'description': f"{'Course inquiry' if is_en else 'استفسار عن دورة'}: {course_name}\n{'Source' if is_en else 'المصدر'}: {'Courses page' if is_en else 'صفحة الدورات'}",
                'type': 'opportunity',
            }

            self._safe_set_field(lead_values, 'crm.lead', 'x_source_type', 'course')
            lead = request.env['crm.lead'].sudo().create(lead_values)
            return {'success': True, 'lead_id': lead.id}

        except Exception as e:
            _logger.error(f'Course registration error: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}