def mark_employee_saved_draft(doc, method=None):
	"""Persist a UI-only marker once an existing draft Timesheet is manually saved."""
	if doc.is_new() or doc.docstatus != 0:
		return

	if getattr(doc, "employee_saved_draft", 0):
		return

	doc.employee_saved_draft = 1
