import json

import frappe

TEMPLATE_PATHS = (
	(
		"leave_approval_notification",
		"leave_approval_notification.json",
	),
	(
		"leave_status_notification",
		"leave_status_notification.json",
	),
)


def _load_template_data(folder_name, file_name):
	path = frappe.get_app_path(
		"finstein_hrms",
		"finstein_hrms",
		"email_template",
		folder_name,
		file_name,
	)

	with open(path) as f:
		return json.load(f)


def execute():
	if not frappe.db.exists("DocType", "Email Template"):
		return

	for folder_name, file_name in TEMPLATE_PATHS:
		template = _load_template_data(folder_name, file_name)

		if frappe.db.exists("Email Template", template["name"]):
			continue

		doc = frappe.new_doc("Email Template")
		doc.name = template["name"]
		doc.subject = template.get("subject")
		doc.response = template.get("response")
		doc.response_html = template.get("response_html")
		doc.use_html = template.get("use_html", 0)
		doc.module = template.get("module")
		doc.insert(ignore_permissions=True)
