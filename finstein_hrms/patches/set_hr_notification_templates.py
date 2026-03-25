import frappe


def execute():
	if not frappe.db.exists("DocType", "HR Settings"):
		return

	settings = frappe.get_single("HR Settings")

	if not settings.leave_approval_notification_template:
		settings.leave_approval_notification_template = "Leave Approval Notification"

	if not settings.leave_status_notification_template:
		settings.leave_status_notification_template = "Leave Status Notification"

	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
