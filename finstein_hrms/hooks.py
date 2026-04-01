app_name = "finstein_hrms"
app_title = "Finstein HRMS"
app_publisher = "Finstein"
app_description = "Custom HRMS extension layer for Finstein on ERPNext"
app_email = "admin@finstein.com"
app_license = "MIT"

fixtures = [
	{"doctype": "Custom DocPerm"},
	{"doctype": "Workflow", "filters": [["is_active", "=", 1]]},
	{
		"doctype": "Notification",
		"filters": [
			[
				"document_type",
				"in",
				[
					"Leave Application",
					"Attendance Request",
					"Expense Claim",
					"Employee Separation",
					"Payroll Entry",
					"Job Requisition",
				],
			]
		],
	},
	{
		"doctype": "Workspace",
		"filters": [
			[
				"name",
				"in",
				[
					"CEO",
					"Employee Workspace",
					"HR Workspace",
					"TL Workspace",
				],
			]
		],
	},
	{"doctype": "Finstein HRMS Settings"},
]

doc_events = {
	"Food Count": {
		"after_insert": "finstein_hrms.scheduled_tasks.update_food_qr_count",
		"on_update": "finstein_hrms.scheduled_tasks.update_food_qr_count",
	},
	"Leave Application": {
		"validate": "finstein_hrms.server_script.leave_validation.validate_leave_dates",
		"before_submit": "finstein_hrms.server_script.leave_validation.check_balance_before_submit",
	},
	"Employee Checkin": {
		"before_save": "finstein_hrms.server_script.checkin_validation.validate_checkin",
		"after_insert": "finstein_hrms.server_script.checkin_validation.sync_attendance_from_checkin",
		"on_update": "finstein_hrms.server_script.checkin_validation.sync_attendance_from_checkin",
	},
	"Attendance Request": {
		"validate": "finstein_hrms.server_script.attendance_request_validation.validate_attendance_request",
	},
	"Interview": {
		"validate": "finstein_hrms.server_script.interview_round.validate_interview_scheduling",
	},
	"Employee Separation": {
		"on_update": "finstein_hrms.server_script.employee_separation_validation.on_update",
	},
	"Expense Claim": {
		"validate": "finstein_hrms.server_script.expense_claim_validation.validate_expense_claim_update",
	},
	"Timesheet": {
		"validate": "finstein_hrms.server_script.timesheet_validation.mark_employee_saved_draft",
	},
}

scheduler_events = {
	"daily": [
		"finstein_hrms.scheduled_tasks.create_food_qr_records",
		"finstein_hrms.scheduled_tasks.escalate_pending_approvals",
		"finstein_hrms.scheduled_tasks.lock_attendance_for_processed_payroll",
	],
	"cron": {
		"0 9 * * *": "finstein_hrms.scheduled_tasks.activate_breakfast_qr",
		"1 11 * * *": "finstein_hrms.scheduled_tasks.mark_breakfast_not_consumed",
		"30 12 * * *": "finstein_hrms.scheduled_tasks.activate_lunch_qr",
		"1 15 * * *": "finstein_hrms.scheduled_tasks.mark_lunch_not_consumed",
		"0 19 * * *": "finstein_hrms.scheduled_tasks.activate_dinner_qr",
		"1 22 * * *": "finstein_hrms.scheduled_tasks.mark_dinner_not_consumed",
	},
}

doctype_js = {
	"Employee Checkin": "public/js/employee_checkin_client.js",
	"Timesheet": "public/js/timesheet.js",
	"Leave Application": "public/js/leave_application.js",
	"Employee Separation": "public/js/employee_separation.js",
	"Attendance Request": "public/js/attendance_request.js",
	"Expense Claim": "public/js/expense_claim.js",
	"Interview": "public/js/interview.js",
	"Payroll Entry": "public/js/payroll_entry.js",
}

doctype_list_js = {
	"Timesheet": "public/js/timesheet_list.js",
}

boot_session = "finstein_hrms.boot.add_navbar_data"

app_include_js = [
	"assets/finstein_hrms/js/fin_notification_sidebar.js?v=2",
]
