/** @odoo-module **/

/**
 * Early Luxon override for Arabic locale to force Latin numerals
 * Waits for Luxon locale to be properly configured before patching
 */

console.log('🔧 Arabic Date Fix: Early Luxon override module loading...');

let checkCount = 0;
const maxChecks = 200; // Wait longer for locale to load

function findAndPatchLuxon() {
    checkCount++;

    const luxonLib = window.luxon;

    if (!luxonLib || !luxonLib.Settings) {
        if (checkCount < maxChecks) {
            setTimeout(findAndPatchLuxon, 50);
        }
        return false;
    }

    // Check if locale is loaded
    const currentLocale = luxonLib.Settings.defaultLocale;
    const currentNumbering = luxonLib.Settings.defaultNumberingSystem;

    // If locale is not set yet, wait more
    if (!currentLocale && checkCount < maxChecks) {
        setTimeout(findAndPatchLuxon, 100);
        return false;
    }

    console.log('✅ Luxon library found at attempt', checkCount);
    console.log('Current Luxon settings:', {
        locale: currentLocale,
        numberingSystem: currentNumbering
    });

    // Only patch if Arabic locale is detected
    if (currentLocale && currentLocale.startsWith('ar')) {
        console.log('🌍 Arabic locale detected:', currentLocale);
        console.log('Current numbering system:', currentNumbering);

        // Check if already using Arab numerals
        if (currentNumbering === 'arab') {
            console.log('📝 Applying Latin numerals patch...');

            // Force Latin numbering system
            luxonLib.Settings.defaultNumberingSystem = 'latn';
            luxonLib.Settings.defaultLocale = 'ar-u-nu-latn';

            // Patch DateTime.prototype methods
            if (luxonLib.DateTime && luxonLib.DateTime.prototype) {
                const originalToFormat = luxonLib.DateTime.prototype.toFormat;
                const originalToLocaleString = luxonLib.DateTime.prototype.toLocaleString;

                luxonLib.DateTime.prototype.toFormat = function(fmt, opts = {}) {
                    const newOpts = { ...opts, numberingSystem: 'latn' };
                    return originalToFormat.call(this, fmt, newOpts);
                };

                luxonLib.DateTime.prototype.toLocaleString = function(formatOpts, opts = {}) {
                    const newOpts = { ...opts, numberingSystem: 'latn' };
                    return originalToLocaleString.call(this, formatOpts, newOpts);
                };

                console.log('✅ DateTime prototype methods patched');
            }

            // Mark as patched
            window.__luxonPatched = true;

            console.log('✅✅ Luxon successfully patched!');
            console.log('New settings:', {
                locale: luxonLib.Settings.defaultLocale,
                numberingSystem: luxonLib.Settings.defaultNumberingSystem
            });

            // Test the patch
            try {
                const testDate = luxonLib.DateTime.now();
                const formatted = testDate.toLocaleString();
                console.log('📅 Test date output:', formatted);

                // Check if it contains Arabic numerals
                if (/[٠-٩]/.test(formatted)) {
                    console.warn('⚠️ Warning: Test still shows Arabic numerals!');
                } else {
                    console.log('✅ Test successful: Using Latin numerals');
                }
            } catch(e) {
                console.warn('⚠️ Test failed:', e);
            }
        } else {
            console.log('✅ Already using Latin numerals, no patch needed');
        }
    } else {
        console.log('ℹ️ Not Arabic locale (' + currentLocale + '), skipping patch');
    }

    return true;
}

// Start searching immediately
findAndPatchLuxon();

// Also try when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.__luxonPatched) {
            console.log('🔄 Retrying Luxon patch after DOMContentLoaded...');
            findAndPatchLuxon();
        }
    });
}

export default {
    findAndPatchLuxon
};