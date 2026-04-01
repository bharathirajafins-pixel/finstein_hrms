frappe.ui.form.on("Timesheet", {
	refresh(frm) {
		_set_saved_indicator(frm);
	},

	after_save(frm) {
		_set_saved_indicator(frm);
		frappe.show_alert(
			{
				message: __("Timesheet saved successfully."),
				indicator: "green",
			},
			5
		);
	},
});

function _set_saved_indicator(frm) {
	if (frm.is_dirty()) {
		return;
	}

	if (frm.doc.docstatus === 0 && !frm.is_new()) {
		setTimeout(() => frm.page.set_indicator(__("Saved"), "green"), 0);
	}
}
