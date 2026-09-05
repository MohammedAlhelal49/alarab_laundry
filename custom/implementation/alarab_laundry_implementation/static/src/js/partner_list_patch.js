import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { unaccent } from "@web/core/utils/strings";

patch(PartnerList.prototype, {
    getPartners() {
        const query = (this.state.query || "").trim().toLowerCase();
        const partners = this.pos.models["res.partner"].getAll();

        // No query → default list
        if (!query) {
            return partners
                .slice(0, 1000)
                .toSorted((a, b) =>
                    this.props.partner?.id === a.id
                        ? -1
                        : (a.name || "").localeCompare(b.name || "")
                );
        }


        const isNumber = /^\d+$/.test(query);

        if (isNumber) {
            return partners.filter((p) => {
                const phone = (p.phone || "").replace(/\D/g, "");
                const mobile = (p.mobile || "").replace(/\D/g, "");
                return phone.includes(query) || mobile.includes(query);
            });
        }


        const searchWord = unaccent(query, false);

        return partners.filter((p) => {
            const name = unaccent((p.name || "").toLowerCase(), false);
            return name.includes(searchWord); // sequence respected
        });
    },
});