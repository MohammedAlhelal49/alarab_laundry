/** © 2025 ehuerta _at_ ixer.mx
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
 */

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useService } from "@web/core/utils/hooks";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(Orderline, {
     props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                uom_rec_id_name: String,
            },
        },
    }
});



patch(ControlButtons.prototype, {
   setup() {
        super.setup();
        this.numberBuffer = useService("number_buffer");
    },

    async onClickUOMSelector() {
	const selectedLine = this.currentOrder.get_selected_orderline();
    if (!selectedLine) {
        this.dialog.add(AlertDialog, {
            title: _t("No product"),
            body: _t("Select a product line first."),
        });
        return;
    }

    let uom_price = null;
           let datas_record = this.pos.models["product.multi.uom.price"].filter(rec => rec.product_id)
            datas_record.forEach((item , index) => {
            console.log(`${item.product_id} , ${item.uom_id.name}  ${item.id}`)
            })


         if (datas_record.filter(rec => rec.product_id.id === selectedLine.product_id.id ).length ) {
        uom_price = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("UOM"),
            list: datas_record.filter((rec) => rec.product_id.id === selectedLine.product_id.id).map((rec) => (
                {id: rec.uom_id.id,
                 label: rec.uom_id.name ,
                 item: rec,
                 isSelected: selectedLine.uom_rec_id ?  selectedLine.uom_rec_id.id == rec.uom_id.id : (selectedLine.product_uom_id && selectedLine.product_uom_id.id == rec.uom_id.id)
                 }))
        });
    }


    else {
       this.dialog.add(AlertDialog, {
            title: _t("No UOM"),
            body: _t(`There is no configured UOM for ${selectedLine.product_id.display_name}`),
        });
        return;
    }
    if (uom_price){
        this.numberBuffer.reset();
        selectedLine.set_uom(uom_price.uom_id);
        selectedLine.set_quantity(0);
    }
   },
});

