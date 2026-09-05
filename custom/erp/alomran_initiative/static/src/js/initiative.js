(function() {
    'use strict';

    // ============================================================
    // POPUP
    // ============================================================
    function showPopup(type, title, msg) {
        var popup = document.getElementById('initiative-popup');
        var icon  = document.getElementById('popup-icon');
        var ttl   = document.getElementById('popup-title');
        var body  = document.getElementById('popup-msg');

        icon.textContent  = type === 'success' ? '✅' : '⚠️';
        ttl.textContent   = title;
        ttl.style.color   = type === 'success' ? '#2e7d32' : '#c62828';
        body.textContent  = msg;
        popup.style.display = 'flex';
    }

    function closePopup() {
        document.getElementById('initiative-popup').style.display = 'none';
    }

    window.closePopup = closePopup;

    // إغلاق عند الضغط خارج الـ box
    document.getElementById('initiative-popup').addEventListener('click', function(e) {
        if (e.target === this) closePopup();
    });

    // ============================================================
    // FORM AJAX SUBMIT
    // ============================================================
    var form = document.querySelector('.application-form__form');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();

        var btn = form.querySelector('button[type="submit"]');
        var originalText = btn.textContent;
        btn.textContent = 'جاري الإرسال...';
        btn.disabled = true;

        var formData = new FormData(form);

        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/initiative/apply', true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onload = function() {
            try {
                var data = JSON.parse(xhr.responseText);
                if (data.success) {
                    showPopup(
                        'success',
                        'تم إرسال طلبك بنجاح! 🎉',
                        'شكراً لتقديمك. سيقوم فريق مركز العمران بمراجعة طلبك والتواصل معك قريباً.\nيرجى العلم أن عدد المقاعد محدود بـ500 مستفيدة.'
                    );
                    form.reset();
                    btn.textContent = originalText;
                    btn.disabled = false;
                } else {
                    showPopup('error', 'تعذّر إرسال الطلب', data.error || 'حدث خطأ، يرجى المحاولة مرة أخرى');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            } catch(err) {
                showPopup('error', 'خطأ في الاتصال', 'تعذّر معالجة الرد من الخادم، يرجى المحاولة مرة أخرى');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        };

        xhr.onerror = function() {
            showPopup('error', 'خطأ في الاتصال', 'تعذّر الاتصال بالخادم، يرجى التحقق من الإنترنت والمحاولة مرة أخرى');
            btn.textContent = originalText;
            btn.disabled = false;
        };

        xhr.send(formData);
    });

})();