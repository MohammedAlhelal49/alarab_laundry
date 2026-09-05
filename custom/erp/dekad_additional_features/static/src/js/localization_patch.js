/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";

/**
 * Convert Arabic numerals to Western
 */
function toWesternNumerals(str) {
    if (!str) return str;
    return str.toString()
        .replace(/٠/g, '0')
        .replace(/١/g, '1')
        .replace(/٢/g, '2')
        .replace(/٣/g, '3')
        .replace(/٤/g, '4')
        .replace(/٥/g, '5')
        .replace(/٦/g, '6')
        .replace(/٧/g, '7')
        .replace(/٨/g, '8')
        .replace(/٩/g, '9');
}

// Double-check Luxon settings when localization loads
if (typeof luxon !== 'undefined' && luxon.Settings) {
    const currentLocale = luxon.Settings.defaultLocale || '';
    if (currentLocale.startsWith('ar')) {
        console.log('Localization patch: Verifying Luxon settings...');

        // Ensure Latin numerals
        if (luxon.Settings.defaultNumberingSystem !== 'latn') {
            console.log('Fixing numbering system to latn');
            luxon.Settings.defaultNumberingSystem = 'latn';
        }

        if (!currentLocale.includes('nu-latn')) {
            console.log('Fixing locale to include nu-latn');
            luxon.Settings.defaultLocale = 'ar-u-nu-latn';
        }

        console.log('Final Luxon settings:', {
            locale: luxon.Settings.defaultLocale,
            numberingSystem: luxon.Settings.defaultNumberingSystem
        });
    }
}

// Patch localization service formatters
patch(localization, {
    formatDate(value, options) {
        let result = super.formatDate(value, options);
        return toWesternNumerals(result);
    },

    formatDateTime(value, options) {
        let result = super.formatDateTime(value, options);
        return toWesternNumerals(result);
    }
});

console.log('✅ Arabic Date Fix: Localization formatters patched');