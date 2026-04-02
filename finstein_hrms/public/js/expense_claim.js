patch_expense_bill_image_upload_behavior();

frappe.ui.form.on("Expense Claim", {
	onload(frm) {
		if (frm.is_new()) {
			auto_fill_employee(frm);
		}

		set_expense_bill_image_required(frm);
	},

	async refresh(frm) {
		if (frm.is_new()) {
			auto_fill_employee(frm);
		}

		set_expense_bill_image_required(frm);
		await toggle_employee_claim_lock(frm);
	},

	validate(frm) {
		validate_expense_bill_images(frm);
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
				frm.set_value("employee", data.name); // From Employee field
				frm.set_value("employee_name", data.employee_name);
				frm.set_value("company", data.company);

				// ─── Make Fields Read Only ───
				frm.set_df_property("employee", "read_only", 1);
				frm.set_df_property("employee_name", "read_only", 1);
				frm.set_df_property("company", "read_only", 1);

				frm.refresh_fields(["employee", "employee_name", "company"]);
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

function set_expense_bill_image_required(frm) {
	const grid = frm.fields_dict.expenses?.grid;
	if (!grid) return;

	grid.toggle_reqd("expense_bill_image", true);
}

function validate_expense_bill_images(frm) {
	(frm.doc.expenses || []).forEach((row) => {
		if (!row.expense_bill_image) {
			frappe.throw(__("Row {0}: Expense Bill Image is mandatory.", [row.idx]));
		}
	});
}

async function toggle_employee_claim_lock(frm) {
	if (!(await should_lock_employee_claim(frm))) {
		return;
	}

	frm.disable_save();
	frm.disable_form();
	lock_expenses_grid(frm);
}

async function should_lock_employee_claim(frm) {
	if (frm.is_new() || frm.doc.workflow_state !== "Pending Approval") {
		return false;
	}

	if (!frappe.user.has_role("Employee")) {
		return false;
	}

	if (frappe.user.has_role(["Administrator", "System Manager", "HR Manager"])) {
		return false;
	}

	const current_employee = await get_current_employee_name();
	return Boolean(current_employee && current_employee === frm.doc.employee);
}

function lock_expenses_grid(frm) {
	const grid = frm.fields_dict.expenses?.grid;
	if (!grid) return;

	grid.cannot_add_rows = true;
	grid.cannot_delete_rows = true;
	(grid.docfields || []).forEach((df) => {
		grid.update_docfield_property(df.fieldname, "read_only", 1);
	});
	grid.debounced_refresh();
}

let current_employee_name_promise;

async function get_current_employee_name() {
	if (!current_employee_name_promise) {
		current_employee_name_promise = frappe.db
			.get_value("Employee", { user_id: frappe.session.user }, "name")
			.then((response) => response.message?.name || null);
	}

	return current_employee_name_promise;
}

function patch_expense_bill_image_upload_behavior() {
	if (frappe.ui.form.ControlAttach.__finstein_expense_claim_patch_applied) {
		return;
	}

	const original_on_upload_complete = frappe.ui.form.ControlAttach.prototype.on_upload_complete;

	frappe.ui.form.ControlAttach.prototype.on_upload_complete = async function (attachment) {
		const is_expense_bill_image =
			this.frm?.doctype === "Expense Claim" && this.df?.fieldname === "expense_bill_image";

		if (!is_expense_bill_image) {
			return original_on_upload_complete.call(this, attachment);
		}

		if (this.frm) {
			await this.parse_validate_and_set_in_model(attachment.file_url);
			this.frm.attachments.update_attachment(attachment);
			this.frm.dirty();
			this.frm.refresh_field(this.df.fieldname);
		}

		this.set_value(attachment.file_url);
	};

	frappe.ui.form.ControlAttach.__finstein_expense_claim_patch_applied = true;
}
