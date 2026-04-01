frappe.ui.form.on("Timesheet", {
	validate(frm) {
		_mark_saved_draft(frm);
	},

	refresh(frm) {
		_set_draft_display_state(frm);
	},

	after_save(frm) {
		_set_draft_display_state(frm);
		if (_is_saved_draft(frm)) {
			frappe.show_alert(
				{
					message: __("Timesheet saved successfully."),
					indicator: "green",
				},
				5
			);
		}
	},
});

function _mark_saved_draft(frm) {
	if (!_has_saved_draft_field(frm)) {
		return;
	}

	if (frm.is_new() || frm.doc.docstatus !== 0) {
		return;
	}

	frm.set_value("employee_saved_draft", 1);
}

function _set_draft_display_state(frm) {
	if (frm.is_dirty() || frm.doc.docstatus !== 0 || frm.is_new()) {
		return;
	}

	if (!_has_saved_draft_field(frm)) {
		setTimeout(() => {
			frm.page.set_indicator(__("Draft"), "red");
			_set_status_field_label(frm, __("Draft"));
		}, 0);
		return;
	}

	if (_is_saved_draft(frm)) {
		setTimeout(() => {
			frm.page.set_indicator(__("Saved"), "green");
			_set_status_field_label(frm, __("Saved"));
		}, 0);
		return;
	}

	setTimeout(() => {
		frm.page.set_indicator(__("Draft"), "red");
		_set_status_field_label(frm, __("Draft"));
	}, 0);
}

function _set_status_field_label(frm, label) {
	const control = frm.get_field("status");
	if (!control || !control.$wrapper) return;

	control.$wrapper.find(".control-input, input, .like-disabled-input").val(label).text(label);
}

function _is_saved_draft(frm) {
	return cint(frm.doc.employee_saved_draft) === 1;
}

function _has_saved_draft_field(frm) {
	return Boolean(frm.fields_dict.employee_saved_draft || frappe.meta.has_field("Timesheet", "employee_saved_draft"));
}
