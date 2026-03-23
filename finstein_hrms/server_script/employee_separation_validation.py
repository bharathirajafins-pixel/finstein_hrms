from datetime import date

import frappe
from frappe import _


def on_update(doc, method=None):
    """Handle Employee Separation approval side effects."""
    if doc.workflow_state == "Approved":
        disable_employee_and_user(doc)


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
