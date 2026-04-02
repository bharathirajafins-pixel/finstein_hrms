import frappe


WORKFLOW_STATE_UPDATES = {
    "Pending HR Review": "Pending TL Approval",
    "Pending Approval": "Pending CEO Approval",
}


def execute():
    if not frappe.db.exists("DocType", "Employee Separation"):
        return

    for old_state, new_state in WORKFLOW_STATE_UPDATES.items():
        frappe.db.sql(
            """
            UPDATE `tabEmployee Separation`
            SET workflow_state = %(new_state)s
            WHERE workflow_state = %(old_state)s
            """,
            {"old_state": old_state, "new_state": new_state},
        )

    frappe.db.commit()
