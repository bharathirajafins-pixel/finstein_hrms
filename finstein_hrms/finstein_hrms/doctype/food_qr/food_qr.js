// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Food QR", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button("Generate QR", function () {
            generate_qr_for_row(frm, 0);
        }).addClass("btn-primary");

        if (frm.doc.qr_data) {
            frm.add_custom_button("Regenerate QR", function () {
                generate_qr_for_row(frm, 1);
            });
        }
    },
});

function generate_qr_for_row(frm, force_regenerate) {
    frappe.call({
        method: "finstein_hrms.finstein_hrms.doctype.food_qr.food_qr.generate_qr",
        args: {
            name: frm.doc.name,
            force_regenerate: force_regenerate ? 1 : 0,
        },
        freeze: true,
        freeze_message: force_regenerate ? "Regenerating QR..." : "Generating QR...",
        callback: function () {
            frappe.show_alert({
                indicator: "green",
                message: force_regenerate ? "QR regenerated" : "QR generated",
            });
            frm.reload_doc();
        },
    });
}
