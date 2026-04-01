const TIMESHEET_SAVED_DRAFT_FIELD = "employee_saved_draft";
const TIMESHEET_HAS_SAVED_DRAFT_FIELD = frappe.meta.has_field(
	"Timesheet",
	TIMESHEET_SAVED_DRAFT_FIELD
);

frappe.listview_settings["Timesheet"] = {
	add_fields: ["status", "total_hours", "start_date", "end_date"].concat(
		TIMESHEET_HAS_SAVED_DRAFT_FIELD ? [TIMESHEET_SAVED_DRAFT_FIELD] : []
	),
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.docstatus === 0 && TIMESHEET_HAS_SAVED_DRAFT_FIELD && cint(doc.employee_saved_draft)) {
			return [__("Saved"), "green", "employee_saved_draft,=,1"];
		}

		if (doc.docstatus === 0) {
			return [__("Draft"), "red", "docstatus,=,0"];
		}

		if (doc.status === "Billed") {
			return [__("Billed"), "green", "status,=,Billed"];
		}

		if (doc.status === "Payslip") {
			return [__("Payslip"), "green", "status,=,Payslip"];
		}

		if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		}
	},
};
