/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ProductConfiguratorPopup } from "@point_of_sale/app/store/product_configurator_popup/product_configurator_popup";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// ============================================================
// Helper: ترجمة ثنائية عربي / إنجليزي
// ============================================================
function t(en, ar) {
    const lang = luxon.Settings.defaultLocale?.split('-')[0] || 'en';
    return lang === 'ar' ? ar : en;
}

// ============================================================
// Helper: اقرأ نوع الـ restriction من إعدادات POS
// ============================================================
function getRestrictionType(pos) {
    if (!pos.config.stock_restriction_enabled) return false;
    return pos.config.stock_restriction_type || false;
}

// ============================================================
// Helper: Goods فقط (consu) — تجاهل service و combo
// ============================================================
function requiresStockCheck(product) {
    const type = product.type ?? product.raw?.type;
    return type === "consu";
}

// ============================================================
// Helper: جلب الكمية real-time + تحديث الـ cache
// ============================================================
async function getLiveQty(orm, product) {
    const result = await orm.call(
        "product.product",
        "read",
        [[product.id], ["qty_available"]]
    );
    const qty = result?.[0]?.qty_available ?? 0;

    // تحديث الـ cache
    if (product.qty_available !== undefined) product.qty_available = qty;
    if (product.raw?.qty_available !== undefined) product.raw.qty_available = qty;

    return qty;
}

// ============================================================
// Patch 1: عند اختيار المنتج — تحديث الـ cache فقط بدون رسائل
// ============================================================
patch(ProductScreen.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async addProductToOrder(product) {
        const hasVariants = product.isConfigurable
            ? product.isConfigurable()
            : (product.variants && product.variants.length > 1);

        if (hasVariants) {
            // باركود يطابق variant واحد بالضبط
            if (this.searchWord) {
                const barcode = this.searchWord;
                const searchedProduct = product.variants?.filter(
                    (p) => p.barcode && p.barcode.includes(barcode)
                );
                if (searchedProduct && searchedProduct.length === 1) {
                    product = searchedProduct[0];
                    // تحديث cache فقط
                    if (requiresStockCheck(product)) {
                        await getLiveQty(this.orm, product);
                    }
                    await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
                    return;
                }
            }
            await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {}, true);

        } else {
            // تحديث cache فقط بدون رسائل
            if (requiresStockCheck(product)) {
                await getLiveQty(this.orm, product);
            }
            await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
        }
    },
});

// ============================================================
// Patch 2: عند اختيار variant — تحديث الـ cache فقط بدون رسائل
// ============================================================
patch(ProductConfiguratorPopup.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async confirm() {
        // نحسب الـ variant الفعلي
        this.computeProductProduct();
        const product = this.state.product;

        // تحديث cache فقط بدون رسائل
        if (product && requiresStockCheck(product)) {
            await getLiveQty(this.orm, product);
        }

        this.props.getPayload(this.computePayload());
        this.props.close();
    },
});

// ============================================================
// Patch 3: عند الضغط على زر Payment — التحقق والرسائل هون فقط
// ============================================================
patch(PosStore.prototype, {

    async pay() {
        const restrictionType = getRestrictionType(this);

        if (restrictionType) {
            const order = this.get_order();
            const lines = order.get_orderlines();
            const orm = this.env.services.orm;
            const dialog = this.env.services.dialog;
            const problematic = [];

            for (const line of lines) {
                const product = line.get_product();

                // تجاهل service و combo
                if (!requiresStockCheck(product)) continue;

                // جلب الكمية real-time
                const liveQty = await getLiveQty(orm, product);
                const requestedQty = line.get_quantity();

                if (requestedQty > liveQty) {
                    problematic.push(
                        `• ${product.display_name}` +
                        `  (${t("Available", "متوفر")}: ${liveQty} | ${t("Requested", "مطلوب")}: ${requestedQty})`
                    );
                }
            }

            if (problematic.length > 0) {
                if (restrictionType === "alert") {
                    const confirmed = await new Promise((resolve) => {
                        dialog.add(ConfirmationDialog, {
                            title: t("⚠️ Stock Warning - Before Completing Sale", "⚠️ تنبيه مخزون - قبل إتمام البيع"),
                            body: t("The following products exceed available quantity:", "المواد التالية تتجاوز الكمية المتوفرة:") +
                                "\n\n" + problematic.join("\n") +
                                "\n\n" + t("Do you want to proceed anyway?", "هل تريد المتابعة رغم ذلك؟"),
                            confirm: () => resolve(true),
                            cancel: () => resolve(false),
                        });
                    });
                    if (!confirmed) return;

                } else if (restrictionType === "block") {
                    dialog.add(AlertDialog, {
                        title: t("🚫 Cannot Complete Sale", "🚫 لا يمكن إتمام البيع"),
                        body: t("The following products exceed available quantity:", "المواد التالية تتجاوز الكمية المتوفرة:") +
                            "\n\n" + problematic.join("\n") +
                            "\n\n" + t("Please adjust the quantities before proceeding.", "يرجى تعديل الكميات قبل المتابعة."),
                    });
                    return;
                }
            }
        }

        return super.pay(...arguments);
    },
});