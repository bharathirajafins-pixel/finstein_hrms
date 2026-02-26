import frappe
from frappe import _
from datetime import date

def on_update(doc, method=None):
    if doc.workflow_state == "Approved":
        disable_employee_and_user(doc)

def disable_employee_and_user(doc, method=None):
    employee = doc.employee

    if not employee:
        frappe.throw(_("Employee is not linked in this separation request."))

    today = date.today().strftime("%Y-%m-%d")

    # ─── Step 1: Change Employee Status to 'Left' + Set Relieving Date ───
    emp_doc = frappe.get_doc("Employee", employee)

    if emp_doc.status == "Left":
        frappe.msgprint(
            _("ℹ️ Employee {0} is already marked as <b>Left</b>.").format(employee)
        )
    else:
        emp_doc.status = "Left"
        emp_doc.relieving_date = today  # ✅ Auto fill Relieving Date with approval date
        emp_doc.save(ignore_permissions=True)
        frappe.msgprint(
            _(
                "✅ Employee <b>{0} - {1}</b> status updated to <b>Left</b> "
                "and Relieving Date set to <b>{2}</b>."
            ).format(
                employee,
                emp_doc.employee_name,
                date.today().strftime("%d-%m-%Y")
            )
        )

    # ─── Step 2: Disable the linked User Account ───
    user_id = frappe.db.get_value("Employee", employee, "user_id")

    if not user_id:
        frappe.msgprint(
            _(
                "⚠️ No User account linked to Employee <b>{0}</b>. "
                "Please disable the user manually if needed."
            ).format(employee)
        )
        return

    user_doc = frappe.get_doc("User", user_id)

    if not user_doc.enabled:
        frappe.msgprint(
            _("ℹ️ User <b>{0}</b> is already disabled.").format(user_id)
        )
    else:
        user_doc.enabled = 0
        user_doc.save(ignore_permissions=True)
        frappe.msgprint(
            _(
                "🚫 User account <b>{0}</b> has been <b>disabled</b>. "
                "The employee can no longer log in."
            ).format(user_id)
        )

    # ─── Step 3: Log the action in the document comments ───
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Employee Separation",
        "reference_name": doc.name,
        "content": (
            f"✅ Employee <b>{emp_doc.employee_name} ({employee})</b> marked as <b>Left</b>. "
            f"Relieving Date set to <b>{date.today().strftime('%d-%m-%Y')}</b>. "
            f"User account <b>{user_id}</b> has been <b>disabled</b>."
        )
    }).insert(ignore_permissions=True)
