const PENDING_APPROVAL_STATES = new Set([
	"Pending TL Approval",
	"Pending CEO Approval",
	"Pending HR Approval",
]);

frappe.ui.form.on("Employee Separation", {
	onload(frm) {
		auto_fill_employee(frm);
	},

	refresh(frm) {
		auto_fill_employee(frm);
		update_employee_workflow_indicator(frm);

		if (frm.is_new() || frm.doc.workflow_state === "Draft") {
			frm.set_df_property("custom_reason", "read_only", 0);
		}
	},
});

function auto_fill_employee(frm) {
	// Only auto fill if it's a new document
	if (!frm.is_new()) return;

	const user_roles = frappe.user_roles || [];

	// Only auto fill for a pure employee user, not approvers/admins
	const is_employee = user_roles.includes("Employee");
	const is_hr = user_roles.includes("HR Manager");
	const is_head = user_roles.includes("Head");
	const is_ceo = user_roles.includes("CEO");
	const is_team_leader = user_roles.includes("Team Leader");

	if (is_employee && !is_hr && !is_head && !is_ceo && !is_team_leader) {
		frappe.db.get_value(
			"Employee",
			{ user_id: frappe.session.user },
			["name", "employee_name", "department", "designation", "company"],
			function (data) {
				if (data) {
					frm.set_value("employee", data.name);
					frm.set_value("employee_name", data.employee_name);
					frm.set_value("department", data.department);
					frm.set_value("designation", data.designation);
					frm.set_value("company", data.company);
					frm.set_df_property("employee", "read_only", 1);
					frm.refresh_fields();
				} else {
					frappe.msgprint({
						title: __("Employee Not Found"),
						message: __(
							"No Employee record linked to your account <b>{0}</b>. Please contact HR to link your user account."
						).replace("{0}", frappe.session.user),
						indicator: "orange",
					});
				}
			}
		);
	}
}

function update_employee_workflow_indicator(frm) {
	if (!is_employee_only_user()) return;
	if (!PENDING_APPROVAL_STATES.has(frm.doc.workflow_state)) return;

	// Let Frappe paint the normal badge first, then replace only the visible label.
	setTimeout(() => {
		frm.page.set_indicator(__("Pending Approval"), "orange");
	}, 0);
}

function is_employee_only_user() {
	const user_roles = frappe.user_roles || [];

	return (
		user_roles.includes("Employee") &&
		!user_roles.includes("HR Manager") &&
		!user_roles.includes("CEO") &&
		!user_roles.includes("Team Leader") &&
		!user_roles.includes("Head") &&
		!user_roles.includes("System Manager")
	);
}
