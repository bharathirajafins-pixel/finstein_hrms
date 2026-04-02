from datetime import date

import frappe
from frappe import _


LEGACY_WORKFLOW_STATE_MAP = {
    "Pending HR Review": "Pending TL Approval",
    "Pending Approval": "Pending CEO Approval",
}

ALLOWED_WORKFLOW_TRANSITIONS = {
    "Draft": {"Draft", "Pending TL Approval"},
    "Pending TL Approval": {"Pending TL Approval", "Pending CEO Approval", "Rejected"},
    "Pending CEO Approval": {"Pending CEO Approval", "Pending HR Approval", "Rejected"},
    "Pending HR Approval": {"Pending HR Approval", "Approved", "Rejected"},
    "Rejected": {"Rejected", "Draft"},
    "Approved": {"Approved"},
}


def validate(doc, method=None):
    """Prevent users from skipping workflow stages by editing workflow_state directly."""
    sync_employee_notification_user(doc)
    validate_workflow_transition(doc)


def on_update(doc, method=None):
    """Handle Employee Separation approval side effects."""
    previous_state = _get_previous_workflow_state(doc)
    current_state = _normalize_workflow_state(getattr(doc, "workflow_state", None))

    if current_state == "Approved" and previous_state != "Approved":
        disable_employee_and_user(doc)


def validate_workflow_transition(doc):
    current_state = _normalize_workflow_state(getattr(doc, "workflow_state", None))
    doc.workflow_state = current_state

    is_new = callable(getattr(doc, "is_new", None)) and doc.is_new()
    previous_state = (
        "Draft"
        if is_new
        else _normalize_workflow_state(
            frappe.db.get_value("Employee Separation", doc.name, "workflow_state")
        )
    )

    allowed_states = ALLOWED_WORKFLOW_TRANSITIONS.get(previous_state)
    if not allowed_states:
        frappe.throw(
            _("Employee Separation is in an unsupported workflow state: {0}.").format(
                previous_state
            )
        )

    if current_state not in allowed_states:
        frappe.throw(
            _(
                "Employee Separation cannot move from {0} to {1}. "
                "Please complete the approval stages in order."
            ).format(previous_state, current_state)
        )


def sync_employee_notification_user(doc):
    if not getattr(doc, "employee", None):
        return

    if not getattr(doc.meta, "get_field", None) or not doc.meta.get_field("employee_user_id"):
        return

    doc.employee_user_id = frappe.db.get_value("Employee", doc.employee, "user_id")


def disable_employee_and_user(doc, method=None):
    """
    Mark employee as Left, set relieving date, disable linked user,
    and add an informational comment on the separation document.
    """
    employee = doc.employee
    if not employee:
        frappe.throw(_("Employee is not linked in this separation request."))

    relieving_date = date.today().strftime("%Y-%m-%d")

    frappe.db.set_value("Employee", employee, "status", "Left")
    frappe.db.set_value("Employee", employee, "relieving_date", relieving_date)

    emp_doc = frappe.get_doc("Employee", employee)
    user_id = emp_doc.user_id

    if user_id:
        frappe.db.set_value("User", user_id, "enabled", 0)

    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Employee Separation",
            "reference_name": doc.name,
            "content": (
                f"Employee <b>{emp_doc.employee_name} ({employee})</b> marked as "
                f"<b>Left</b>. Relieving Date set to <b>{relieving_date}</b>."
                + (f" User account <b>{user_id}</b> disabled." if user_id else "")
            ),
        }
    ).insert(ignore_permissions=True)


def _normalize_workflow_state(state):
    if state in (None, ""):
        return "Draft"

    if isinstance(state, str):
        state = state.strip()

    return LEGACY_WORKFLOW_STATE_MAP.get(state, state)


def _get_previous_workflow_state(doc):
    get_previous = getattr(doc, "get_doc_before_save", None)
    if not callable(get_previous):
        return None

    previous_doc = get_previous()
    previous_state = getattr(previous_doc, "workflow_state", None)

    if previous_state is not None and not isinstance(previous_state, str):
        return None

    return _normalize_workflow_state(previous_state)
