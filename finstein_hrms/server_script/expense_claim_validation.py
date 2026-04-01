import frappe
from frappe import _

LOCKED_WORKFLOW_STATES = {"Pending Approval"}
PRIVILEGED_ROLES = {"Administrator", "System Manager", "HR Manager"}


def validate_expense_claim_update(doc, method=None):
	"""Block employee-side edits once the claim is saved for approval."""
	if doc.is_new():
		return

	previous = frappe.db.get_value(
		"Expense Claim",
		doc.name,
		["employee", "workflow_state"],
		as_dict=True,
	)
	if not previous or previous.workflow_state not in LOCKED_WORKFLOW_STATES:
		return

	if not _is_employee_owner(previous.employee):
		return

	frappe.throw(_("You cannot edit this Expense Claim after it is saved and pending approval."))


def _is_employee_owner(employee):
	employee_user = frappe.db.get_value("Employee", employee, "user_id")
	if not employee_user or employee_user != frappe.session.user:
		return False

	return not bool(PRIVILEGED_ROLES.intersection(frappe.get_roles()))
