# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
from datetime import datetime, timedelta
import re
import json
import logging

_logger = logging.getLogger(__name__)

BRANCH_COMPANY_MAPPING = {
    'وسط المدينة - العين':    'Al Murabba',
    'اليحر مول - العين':      'Al Yahr Branch',
    'مكاني مول زاخر - العين': 'Zakhir Branch',
    'البراري مول - العين':    'Al Barari Mall Branch',
    'الفوعة مول - العين':     'Al Foaa Branch',
    'مزيد مول - ابوظبي':      'Mazyad Mall Branch',
    'شارع المرور - ابوظبي':   'Al Meroor Branch',
    'القرهود - دبي':          'Al Garhoud Branch',
    'البرشا - دبي':           'Al Barsha Branch',
    'سنترال مول - الشارقة':   'AL OMRAN EDUCATION LANGUAGES CENTER L.L.C',
    'راك مول - راس الخيمة':   'Ras Al Khaimah Branch',
    'برج العوضي - الفجيرة':   '-ALOMRAN FOR TRAINING AND DEVELOPING CENTER LLC-',
}

# ============================================================
# VALIDATION HELPERS
# ============================================================

def _sanitize(value, max_len=500):
    """تنظيف المدخلات من XSS"""
    if not value:
        return ''
    value = str(value).strip()
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    value = value.replace('"', '&quot;').replace("'", '&#x27;')
    return value[:max_len]

def _validate_emirates_id(eid):
    """الهوية الإماراتية: 15 رقم تبدأ بـ 784"""
    cleaned = re.sub(r'[-\s]', '', eid)
    return bool(re.match(r'^784\d{12}$', cleaned)), cleaned

def _validate_phone(phone):
    """هاتف إماراتي: يبدأ بـ 05 أو +9715"""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    if cleaned.startswith('+971'):
        cleaned = '0' + cleaned[4:]
    elif cleaned.startswith('971'):
        cleaned = '0' + cleaned[3:]
    return bool(re.match(r'^0[0-9]{9}$', cleaned)), cleaned

def _validate_email(email):
    """التحقق من صيغة الإيميل"""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def _is_duplicate(phone, emirates_id):
    """منع تكرار التسجيل بنفس الهاتف أو الهوية خلال 24 ساعة"""
    try:
        yesterday = datetime.now() - timedelta(hours=24)
        domain = [
            ('tag_ids.name', '=', 'مبادرة المرأة الإماراتية'),
            ('create_date', '>=', yesterday.strftime('%Y-%m-%d %H:%M:%S')),
            '|',
            ('phone', '=', phone),
            ('description', 'ilike', emirates_id),
        ]
        return request.env['crm.lead'].sudo().search_count(domain) > 0
    except Exception as e:
        _logger.warning('Duplicate check error: %s', e)
        return False

def _get_utm_source(source_name):
    """جلب أو إنشاء UTM source"""
    try:
        utm = request.env['utm.source'].sudo().search(
            [('name', '=', source_name)], limit=1)
        if not utm:
            utm = request.env['utm.source'].sudo().create({'name': source_name})
        return utm.id
    except Exception:
        return False


class InitiativeController(http.Controller):

    def _get_company_and_salesperson(self, branch):
        company_id = False
        salesperson_id = False
        company_name = BRANCH_COMPANY_MAPPING.get(branch)
        if not company_name:
            return company_id, salesperson_id
        company = request.env['res.company'].sudo().search(
            [('name', '=', company_name)], limit=1)
        if not company:
            return company_id, salesperson_id
        company_id = company.id
        sales_admin_group = request.env.ref(
            'sales_team.group_sale_manager', raise_if_not_found=False)
        if sales_admin_group:
            admin_user = request.env['res.users'].sudo().search([
                ('groups_id', 'in', sales_admin_group.id),
                ('company_ids', 'in', company_id),
                ('active', '=', True),
            ], limit=1)
            if admin_user:
                salesperson_id = admin_user.id
        return company_id, salesperson_id

    def _render_page(self, success=False, error=''):
        try:
            csrf = request.csrf_token()
        except Exception:
            csrf = ''

        success_html = ''
        error_html = ''

        if success:
            success_html = '''
            <div class="success-state">
                <div class="success-state__icon">
                    <svg viewBox="0 0 48 48" fill="none">
                        <circle cx="24" cy="24" r="23" stroke="#406AB3" stroke-width="2"/>
                        <path d="M14 24l7 7 13-13" stroke="#406AB3" stroke-width="2.5"
                              stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <h3 class="success-state__title">شكراً لتقديمك!</h3>
                <p class="success-state__text">سيقوم فريق مركز العمران بمراجعة الطلبات وفق شروط المبادرة.</p>
                <p class="success-state__text success-state__text--note">
                    يرجى العلم أن تعبئة النموذج لا تعني القبول النهائي،
                    وأن عدد المقاعد محدود بـ500 مستفيدة.
                </p>
            </div>'''

        if error:
            error_html = (
                f'<div style="background:#ffebee;color:#c62828;padding:1rem 2rem;'
                f'text-align:center;border-radius:8px;margin-bottom:1rem;">⚠️ {error}</div>'
            )

        form_html = '' if success else f'''
        {error_html}
        <form class="application-form__form" action="/initiative/apply" method="post">
            <input type="hidden" name="csrf_token" value="{csrf}">
            <!-- honeypot: مخفي عن البشر، بيتعبى بالـ bots -->
            <input type="text" name="_trap" value="" style="display:none!important" tabindex="-1" autocomplete="off">
            <div class="form-grid">
                <div class="form-field">
                    <label class="form-field__label">الاسم الكامل <span style="color:#e53e3e">*</span></label>
                    <input type="text" name="fullName" class="form-field__input" required maxlength="100">
                </div>
                <div class="form-field">
                    <label class="form-field__label">رقم الهوية الإماراتية <span style="color:#e53e3e">*</span></label>
                    <input type="text" name="emiratesId" class="form-field__input" required
                           inputmode="numeric" placeholder="784-XXXX-XXXXXXX-X" maxlength="20">
                </div>
                <div class="form-field">
                    <label class="form-field__label">رقم الهاتف <span style="color:#e53e3e">*</span></label>
                    <input type="tel" name="phone" class="form-field__input" required
                           dir="ltr" placeholder="05X XXX XXXX" maxlength="15">
                </div>
                <div class="form-field">
                    <label class="form-field__label">البريد الإلكتروني <span style="color:#e53e3e">*</span></label>
                    <input type="email" name="email" class="form-field__input" required
                           dir="ltr" maxlength="150">
                </div>
                <div class="form-field form-field--full">
                    <label class="form-field__label">الفرع المفضل للدراسة <span style="color:#e53e3e">*</span></label>
                    <select name="branch" class="form-field__select" required>
                        <option value="" disabled selected>اختر الفرع</option>
                        <optgroup label="العين">
                            <option value="وسط المدينة - العين">وسط المدينة</option>
                            <option value="اليحر مول - العين">اليحر مول</option>
                            <option value="مكاني مول زاخر - العين">مكاني مول زاخر</option>
                            <option value="البراري مول - العين">البراري مول</option>
                            <option value="الفوعة مول - العين">الفوعة مول</option>
                        </optgroup>
                        <optgroup label="أبوظبي">
                            <option value="مزيد مول - ابوظبي">مزيد مول</option>
                            <option value="شارع المرور - ابوظبي">شارع المرور</option>
                        </optgroup>
                        <optgroup label="دبي">
                            <option value="القرهود - دبي">القرهود</option>
                            <option value="البرشا - دبي">البرشا</option>
                        </optgroup>
                        <optgroup label="الشارقة">
                            <option value="سنترال مول - الشارقة">سنترال مول</option>
                        </optgroup>
                        <optgroup label="رأس الخيمة">
                            <option value="راك مول - راس الخيمة">راك مول</option>
                        </optgroup>
                        <optgroup label="الفجيرة">
                            <option value="برج العوضي - الفجيرة">برج العوضي</option>
                        </optgroup>
                    </select>
                </div>
                <div class="form-field form-field--full">
                    <label class="form-field__label">مستوى اللغة الإنجليزية <span style="color:#e53e3e">*</span></label>
                    <select name="englishLevel" class="form-field__select" required>
                        <option value="" disabled selected>اختر المستوى</option>
                        <option value="beginner">مبتدئ / Beginner</option>
                        <option value="intermediate">متوسط / Intermediate</option>
                        <option value="good">جيد / Good</option>
                        <option value="advanced">متقدم / Advanced</option>
                        <option value="unknown">لا أعرف / Not Sure</option>
                    </select>
                </div>
                <div class="form-field form-field--full">
                    <label class="form-field__label">لماذا ترغبين في المشاركة؟ <span style="color:#e53e3e">*</span></label>
                    <textarea name="reason" class="form-field__textarea" rows="4"
                              required maxlength="1000"></textarea>
                </div>
                <div class="form-field">
                    <label class="form-field__label">هل يمكنكِ الالتزام بساعة ونصف، ثلاثة أيام أسبوعياً؟</label>
                    <div class="form-field__radio-group">
                        <label class="form-field__radio">
                            <input type="radio" name="timeCommitment" value="yes" required>
                            <span class="form-field__radio-mark"></span><span>نعم</span>
                        </label>
                        <label class="form-field__radio">
                            <input type="radio" name="timeCommitment" value="no">
                            <span class="form-field__radio-mark"></span><span>لا</span>
                        </label>
                    </div>
                </div>
                <div class="form-field">
                    <label class="form-field__label">هل أنتِ مستعدة للالتزام بالحضور طوال البرنامج؟</label>
                    <div class="form-field__radio-group">
                        <label class="form-field__radio">
                            <input type="radio" name="fullProgram" value="yes" required>
                            <span class="form-field__radio-mark"></span><span>نعم</span>
                        </label>
                        <label class="form-field__radio">
                            <input type="radio" name="fullProgram" value="no">
                            <span class="form-field__radio-mark"></span><span>لا</span>
                        </label>
                    </div>
                </div>
            </div>
            <fieldset class="form-confirmations">
                <div class="form-confirmation">
                    <label class="form-field__checkbox">
                        <input type="checkbox" name="confirm1" required>
                        <span class="form-field__checkbox-mark"></span>
                        <span>أقر بأنني امرأة إماراتية وأبلغ من العمر 18 عاماً أو أكثر، وأن البيانات صحيحة.</span>
                    </label>
                </div>
                <div class="form-confirmation">
                    <label class="form-field__checkbox">
                        <input type="checkbox" name="confirm2" required>
                        <span class="form-field__checkbox-mark"></span>
                        <span>أوافق على شروط وأحكام المبادرة وآلية اختيار المستفيدات.</span>
                    </label>
                </div>
            </fieldset>
            <div class="form-actions">
                <button type="submit" class="btn btn--primary btn--lg btn--full">
                    إرسال طلب المشاركة
                </button>
            </div>
        </form>'''

        html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مبادرة العمران لتمكين المرأة الإماراتية | 500 فرصة تعليمية مجانية</title>
    <meta name="description" content="مبادرة مجتمعية بقيمة 5 ملايين درهم لتوفير سنة كاملة من تعلم اللغة الإنجليزية مجاناً لـ500 امرأة إماراتية.">
    <meta name="robots" content="index, follow">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@300;400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="icon" type="image/png" href="/alomran_initiative/static/src/img/favicon.png">
    <link rel="stylesheet" href="/alomran_initiative/static/src/css/initiative.css">
</head>
<body>

<header class="site-header">
    <div class="container">
        <a href="/initiative" class="logo">
            <img src="/alomran_initiative/static/src/img/omran-full-logo.png"
                 alt="مركز العمران للتدريب والتطوير" width="240" height="60">
        </a>
        <nav class="main-nav">
            <ul class="nav-list">
                <li><a href="#provide" class="nav-link">ماذا نقدم</a></li>
                <li><a href="#requirements" class="nav-link">الشروط</a></li>
                <li><a href="#selection" class="nav-link">آلية الاختيار</a></li>
                <li><a href="#locations" class="nav-link">الفروع</a></li>
                <li><a href="#apply" class="nav-link nav-cta">قدمي طلبك الآن</a></li>
                <li>
                    <a href="/ar" class="nav-link"
                       style="display:flex;align-items:center;gap:6px;border:1px solid rgba(255,255,255,0.4);border-radius:50px;padding:6px 16px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                             stroke="currentColor" stroke-width="2">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                            <polyline points="9 22 9 12 15 12 15 22"/>
                        </svg>
                        الموقع الرئيسي
                    </a>
                </li>
            </ul>
        </nav>
    </div>
</header>

<main>
    <section class="hero" id="hero">
        <div class="container">
            <div class="hero-content">
                <div class="hero-badge">
                    <svg class="icon" width="20" height="20" viewBox="0 0 24 24"
                         fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    <span>مبادرة مجتمعية</span>
                </div>
                <h1 class="hero-title">مبادرة العمران لتمكين المرأة الإماراتية</h1>
                <p class="hero-subtitle">5 ملايين درهم لدعم تعليم المرأة الإماراتية</p>
                <div class="hero-copy">
                    <p>بمناسبة يوم المرأة الإماراتية، يطلق مركز العمران للتدريب والتطوير مبادرة
                       مجتمعية بقيمة 5,000,000 درهم، لتوفير فرصة تعليمية مجانية لـ 500 امرأة
                       إماراتية لتعلم اللغة الإنجليزية لمدة عام كامل.</p>
                    <p class="hero-statement">لأن تمكين المرأة يبدأ بالعلم، ولأن طموح المرأة
                       الإماراتية يستحق أن يجد من يدعمه.</p>
                </div>
                <div class="hero-actions">
                    <a href="#apply" class="btn btn-primary">قدمي طلبك الآن</a>
                </div>
            </div>
            <div class="hero-image">
                <img src="/alomran_initiative/static/src/img/emirati-woman.jpg"
                     alt="امرأة إماراتية في بيئة تعليمية" loading="eager" width="800" height="600">
                <div class="hero-image-badge">
                    <span class="badge-number">500</span>
                    <span class="badge-text">فرصة تعليمية</span>
                </div>
            </div>
        </div>
        <div class="hero-decoration" aria-hidden="true">
            <svg class="decoration-arc" viewBox="0 0 400 400" width="400" height="400">
                <circle cx="200" cy="200" r="180" fill="none" stroke="#406AB2"
                        stroke-width="2" opacity="0.1"/>
                <circle cx="200" cy="200" r="150" fill="none" stroke="#60BB46"
                        stroke-width="1" opacity="0.1"/>
            </svg>
        </div>
    </section>

    <section class="statistics" id="statistics">
        <div class="container">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></div>
                    <div class="stat-number">5,000,000</div>
                    <div class="stat-label">درهم قيمة المبادرة</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg></div>
                    <div class="stat-number">500</div>
                    <div class="stat-label">امرأة إماراتية</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
                    <div class="stat-number">سنة كاملة</div>
                    <div class="stat-label">من التعليم</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
                    <div class="stat-number">بدون رسوم</div>
                    <div class="stat-label">دراسة اللغة الإنجليزية</div>
                </div>
            </div>
        </div>
    </section>

    <section class="features" id="provide">
        <div class="container">
            <div class="section-header">
                <h2 class="section-title">ماذا نقدم لكِ؟</h2>
                <p class="section-subtitle">سنة كاملة من تعلم اللغة الإنجليزية مجاناً</p>
            </div>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg></div>
                    <h3 class="feature-title">سنة دراسية كاملة</h3>
                    <p class="feature-text">سنة دراسية كاملة لتعلم وتطوير مهارات اللغة الإنجليزية.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
                    <h3 class="feature-title">مهارات تواصل أقوى</h3>
                    <p class="feature-text">تطوير مهارات التواصل من خلال التدريب على المحادثة والاستماع والقراءة والكتابة.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div>
                    <h3 class="feature-title">دراسة حضورية</h3>
                    <p class="feature-text">دراسة حضورية في أحد فروع مركز العمران في مختلف إمارات الدولة.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
                    <h3 class="feature-title">بدون رسوم دراسية</h3>
                    <p class="feature-text">تتحمل المبادرة تكلفة البرنامج التعليمي للمستفيدات المقبولات.</p>
                </div>
            </div>
        </div>
    </section>

    <section class="why" id="why">
        <div class="container">
            <div class="section-header"><h2 class="section-title">لماذا أطلقنا هذه المبادرة؟</h2></div>
            <div class="why-content">
                <div class="why-text">
                    <p>نؤمن في مركز العمران أن الاستثمار الحقيقي هو الاستثمار في الإنسان.</p>
                    <p>والمرأة الإماراتية كانت ولا تزال شريكاً أساسياً في مسيرة التنمية والنجاح.</p>
                    <p>لذلك، وبمناسبة يوم المرأة الإماراتية، أردنا أن نقدم مبادرة يكون أثرها عملياً ومستداماً.</p>
                </div>
                <div class="why-stats">
                    <div class="why-stat"><div class="why-stat-number">5 ملايين درهم</div><div class="why-stat-label">في التعليم</div></div>
                    <div class="why-stat"><div class="why-stat-number">500 فرصة</div><div class="why-stat-label">تعليمية حقيقية</div></div>
                    <div class="why-stat"><div class="why-stat-number">500 قصة نجاح</div><div class="why-stat-label">محتملة</div></div>
                </div>
            </div>
        </div>
    </section>

    <section class="requirements" id="requirements">
        <div class="container">
            <div class="section-header">
                <h2 class="section-title">من يمكنها التقديم؟</h2>
                <p class="section-intro">المبادرة مخصصة للمرأة الإماراتية التي تنطبق عليها الشروط التالية:</p>
            </div>
            <div class="requirements-list">
                <div class="requirement-item"><div class="requirement-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div><p>أن تكون المتقدمة امرأة إماراتية.</p></div>
                <div class="requirement-item"><div class="requirement-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div><p>أن يكون عمرها 18 عاماً أو أكثر.</p></div>
                <div class="requirement-item"><div class="requirement-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div><p>أن تكون متفرغة لمدة ساعة ونصف، ثلاثة أيام أسبوعياً.</p></div>
                <div class="requirement-item"><div class="requirement-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div><p>أن تكون جادة وقادرة على الالتزام بالحضور والدوام طوال فترة البرنامج.</p></div>
            </div>
            <div class="requirements-cta">
                <p>إذا كنتِ مستعدة لاستثمار وقتك في نفسك وتطوير مستقبلك، فهذه الفرصة لكِ.</p>
                <a href="#apply" class="btn btn-primary">أريد التقديم على المبادرة</a>
            </div>
        </div>
    </section>

    <section class="selection" id="selection">
        <div class="container">
            <div class="section-header"><h2 class="section-title">كيف يتم اختيار المستفيدات؟</h2></div>
            <div class="process-timeline">
                <div class="process-step"><div class="step-number">01</div><div class="step-content"><h3>مطابقة شروط المبادرة</h3><p>التأكد من استيفاء المتقدمة لجميع الشروط المطلوبة.</p></div></div>
                <div class="process-step"><div class="step-number">02</div><div class="step-content"><h3>أولوية التقديم</h3><p>تُؤخذ أولوية التقديم بعين الاعتبار ضمن آلية اختيار المستفيدات.</p></div></div>
                <div class="process-step"><div class="step-number">03</div><div class="step-content"><h3>ترشيحات المؤسسات الداعمة للمرأة</h3><p>سيتم استكمال العدد المستهدف من خلال ترشيحات المؤسسات الحكومية.</p></div></div>
            </div>
        </div>
    </section>

    <section class="locations" id="locations">
        <div class="container">
            <div class="section-header">
                <h2 class="section-title">أين ستكون الدراسة؟</h2>
                <p class="section-intro">تتوفر الدراسة من خلال فروع مركز العمران في مختلف إمارات دولة الإمارات العربية المتحدة.</p>
            </div>
            <div class="emirates-grid">
                {''.join([
                    f'<div class="emirate-chip">'
                    f'<svg class="chip-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
                    f'<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
                    f'<circle cx="12" cy="10" r="3"/></svg>'
                    f'<span>{e}</span></div>'
                    for e in ['أبوظبي','دبي','الشارقة','عجمان','أم القيوين','رأس الخيمة','الفجيرة']
                ])}
            </div>
        </div>
    </section>

    <section class="emotional-cta" id="emotional-cta">
        <div class="container">
            <div class="emotional-content">
                <h2 class="emotional-title">هل أنتِ مستعدة لتبدئي؟</h2>
                <div class="emotional-text">
                    <p>قد تكون ساعة ونصف، ثلاثة أيام في الأسبوع، هي الوقت الذي تستثمرينه اليوم،
                       لكن المهارة قد ترافقك لسنوات قادمة.</p>
                    <p class="emotional-highlight">لكننا نعدكِ بفرصة حقيقية لتبدئي التغيير.</p>
                </div>
                <a href="#apply" class="btn btn-primary btn-large">قدمي طلبك الآن</a>
            </div>
        </div>
    </section>

    <section class="application-form" id="apply">
        <div class="container">
            <div class="section-header">
                <h2 class="section-header__title">قدمي طلبك للمشاركة</h2>
                <p class="section-header__subtitle">املئي البيانات التالية وسيتواصل معك فريق المبادرة</p>
            </div>
            {success_html if success else form_html}
        </div>
    </section>

    <section class="final-statement">
        <div class="container">
            <div class="statement-content">
                <div class="statement-amount">5,000,000 درهم</div>
                <h2 class="statement-heading">استثمار في الإنسان، احتفاءً بالمرأة الإماراتية</h2>
                <div class="statement-brand">
                    <img src="/alomran_initiative/static/src/img/omran-full-logo.png"
                         alt="مركز العمران" width="240" height="60">
                    <p class="statement-name">مركز العمران للتدريب والتطوير</p>
                </div>
                <a href="#apply" class="btn btn-primary">قدمي طلبك الآن</a>
            </div>
        </div>
    </section>
</main>

<footer class="site-footer">
    <div class="container">
        <div class="footer-content">
            <div class="footer-brand">
                <img src="/alomran_initiative/static/src/img/omran-full-logo.png"
                     alt="مركز العمران للتدريب والتطوير" width="240" height="60">
                <p class="footer-name">مركز العمران للتدريب والتطوير</p>
                <p class="footer-initiative">المبادرة المجتمعية لتمكين المرأة الإماراتية</p>
            </div>
            <nav class="footer-nav" aria-label="تنقل التذييل">
                <ul class="footer-links">
                    <li><a href="#provide">ماذا نقدم</a></li>
                    <li><a href="#requirements">الشروط</a></li>
                    <li><a href="#selection">آلية الاختيار</a></li>
                    <li><a href="#locations">الفروع</a></li>
                    <li><a href="#apply">التقديم</a></li>
                </ul>
            </nav>
            <div class="footer-legal">
                <a href="#" class="footer-legal-link">سياسة الخصوصية</a>
                <a href="#" class="footer-legal-link">الشروط والأحكام</a>
            </div>
        </div>
        <div class="footer-bottom">
            <p>&copy; 2026 مركز العمران للتدريب والتطوير. جميع الحقوق محفوظة.</p>
        </div>
    </div>
</footer>

<!-- Popup Notification -->
<div id="initiative-popup" style="
    display:none;position:fixed;inset:0;
    background:rgba(0,0,0,0.6);z-index:9999;
    align-items:center;justify-content:center;">
    <div style="
        background:#fff;border-radius:20px;padding:2.5rem;
        max-width:480px;width:90%;text-align:center;
        font-family:Alexandria,sans-serif;direction:rtl;
        box-shadow:0 20px 60px rgba(0,0,0,0.3);animation:popupIn 0.3s ease;">
        <div id="popup-icon" style="font-size:3.5rem;margin-bottom:1rem;"></div>
        <h3 id="popup-title" style="margin-bottom:0.75rem;font-size:1.3rem;"></h3>
        <p id="popup-msg" style="color:#555;margin-bottom:1.5rem;line-height:1.7;white-space:pre-line;"></p>
        <button onclick="closePopup()" style="
            background:linear-gradient(135deg,#406AB2,#60BB46);
            color:#fff;border:none;border-radius:50px;
            padding:0.75rem 2.5rem;font-size:1rem;
            font-family:Alexandria,sans-serif;cursor:pointer;">
            حسناً
        </button>
    </div>
</div>

<style>
@keyframes popupIn {{
    from {{ opacity:0; transform:scale(0.85); }}
    to   {{ opacity:1; transform:scale(1); }}
}}
</style>

<script src="/alomran_initiative/static/src/js/initiative.js"></script>
</body>
</html>'''

        response = Response(html, content_type='text/html;charset=utf-8')
        # Cache للصفحة الثابتة
        response.headers['Cache-Control'] = 'public, max-age=1800'
        return response

    @http.route('/initiative', type='http', auth='public', website=False, sitemap=True, csrf=False)
    def initiative_page(self, **kwargs):
        return self._render_page()

    @http.route('/initiative/apply', type='http', auth='public', website=False, methods=['POST'], csrf=False)
    def initiative_apply(self, **post):
        try:
            # ===== Honeypot Check =====
            if post.get('_trap', '') != '':
                _logger.warning('Initiative: honeypot triggered — bot detected')
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': True}), content_type='application/json')
                return self._render_page(success=True)

            # ===== Sanitization =====
            full_name   = _sanitize(post.get('fullName', ''), 100)
            emirates_id = _sanitize(post.get('emiratesId', ''), 20)
            phone       = _sanitize(post.get('phone', ''), 15)
            email       = _sanitize(post.get('email', ''), 150)
            branch      = post.get('branch', '').strip()
            english_lvl = post.get('englishLevel', '').strip()
            reason      = _sanitize(post.get('reason', ''), 1000)
            time_commit = post.get('timeCommitment', '').strip()
            full_prog   = post.get('fullProgram', '').strip()

            # ===== Required Fields =====
            if not all([full_name, emirates_id, phone, email, branch]):
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'يرجى ملء جميع الحقول المطلوبة'}), content_type='application/json')
                return self._render_page(error='يرجى ملء جميع الحقول المطلوبة')

            # ===== Validation =====
            eid_valid, emirates_id_clean = _validate_emirates_id(emirates_id)
            if not eid_valid:
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'رقم الهوية الإماراتية غير صحيح — يجب أن يبدأ بـ 784 ويتكون من 15 رقم'}), content_type='application/json')
                return self._render_page(error='رقم الهوية الإماراتية غير صحيح — يجب أن يبدأ بـ 784 ويتكون من 15 رقم')

            phone_valid, phone_clean = _validate_phone(phone)
            if not phone_valid:
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'رقم الهاتف غير صحيح — يرجى إدخال رقم إماراتي صحيح'}), content_type='application/json')
                return self._render_page(error='رقم الهاتف غير صحيح — يرجى إدخال رقم إماراتي صحيح')

            if not _validate_email(email):
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'البريد الإلكتروني غير صحيح'}), content_type='application/json')
                return self._render_page(error='البريد الإلكتروني غير صحيح')

            # Branch validation
            if branch not in BRANCH_COMPANY_MAPPING:
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'يرجى اختيار فرع صحيح'}), content_type='application/json')
                return self._render_page(error='يرجى اختيار فرع صحيح')

            # ===== Rate Limiting =====
            if _is_duplicate(phone_clean, emirates_id_clean):
                if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(json.dumps({'success': False, 'error': 'لقد سجّلتِ مسبقاً في المبادرة خلال الـ 24 ساعة الماضية'}), content_type='application/json')
                return self._render_page(error='لقد سجّلتِ مسبقاً في المبادرة خلال الـ 24 ساعة الماضية')

            # ===== UTM Tracking =====
            utm_source_id = False
            try:
                utm_source = request.httprequest.cookies.get('utm_source') \
                             or request.httprequest.args.get('utm_source', '')
                if utm_source:
                    utm_source_id = _get_utm_source(_sanitize(utm_source, 50))
            except Exception:
                pass

            # ===== Build Description =====
            description = (
                "مبادرة المرأة الإماراتية - طلب مشاركة\n"
                "=======================================\n"
                f"الاسم الكامل:       {full_name}\n"
                f"رقم الهوية:         {emirates_id_clean}\n"
                f"الهاتف:             {phone_clean}\n"
                f"البريد الإلكتروني:  {email}\n"
                f"الفرع المفضل:       {branch}\n"
                f"مستوى اللغة:        {english_lvl}\n"
                f"الالتزام بالوقت:    {time_commit}\n"
                f"الالتزام بالبرنامج: {full_prog}\n"
                "\n"
                "سبب الرغبة في المشاركة:\n"
                f"{reason}"
            )

            # ===== CRM Tag =====
            tag = request.env['crm.tag'].sudo().search(
                [('name', '=', 'مبادرة المرأة الإماراتية')], limit=1)
            if not tag:
                tag = request.env['crm.tag'].sudo().create(
                    {'name': 'مبادرة المرأة الإماراتية'})

            # ===== Company & Salesperson =====
            company_id, salesperson_id = self._get_company_and_salesperson(branch)

            # ===== Stage =====
            stage = request.env['crm.stage'].sudo().search([], limit=1)

            # ===== Create Lead =====
            lead_vals = {
                'name': f'مبادرة المرأة - {full_name}',
                'contact_name': full_name,
                'phone': phone_clean,
                'email_from': email,
                'description': description,
                'tag_ids': [(4, tag.id)],
                'partner_name': full_name,
                'type': 'lead',
                'company_id': company_id,
                'user_id': salesperson_id,
            }
            if stage:
                lead_vals['stage_id'] = stage.id
            if utm_source_id:
                lead_vals['source_id'] = utm_source_id

            request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info('Initiative OK: %s - %s - %s', full_name, phone_clean, branch)

            # AJAX response
            if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return Response(
                    json.dumps({'success': True}),
                    content_type='application/json'
                )
            return self._render_page(success=True)

        except Exception as e:
            _logger.error('Initiative error: %s', str(e), exc_info=True)
            if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return Response(
                    json.dumps({'success': False, 'error': 'حدث خطأ، يرجى المحاولة مرة أخرى'}),
                    content_type='application/json'
                )
            return self._render_page(error='حدث خطأ، يرجى المحاولة مرة أخرى')