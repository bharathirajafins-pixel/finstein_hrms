frappe.ui.form.on("Attendance Request", {
	onload(frm) {
		if (frm.is_new()) {
			auto_fill_employee(frm);
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			auto_fill_employee(frm);
		}
	},
});

function auto_fill_employee(frm) {
	frappe.db.get_value(
		"Employee",
		{ user_id: frappe.session.user },
		["name", "employee_name", "company"],
		function (data) {
			if (data && data.name) {
				// ─── Auto Fill Fields ───
				frm.set_value("employee", data.name);
				frm.set_value("company", data.company);

				// ─── Make Fields Read Only ───
				frm.set_df_property("employee", "read_only", 1);
				frm.set_df_property("company", "read_only", 1);

				frm.refresh_fields(["employee", "company"]);
			} else {
				frappe.msgprint({
					title: __("Employee Not Found"),
					message: __(
						"⚠️ No Employee record linked to your account <b>" +
							frappe.session.user +
							"</b>. Please contact HR."
					),
					indicator: "orange",
				});
			}
		}
	);
}
