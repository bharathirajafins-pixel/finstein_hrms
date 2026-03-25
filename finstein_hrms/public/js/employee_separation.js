frappe.ui.form.on('Employee Separation', {

    onload(frm) {
        auto_fill_employee(frm);
    },

    refresh(frm) {
        auto_fill_employee(frm);
        if (frm.is_new() || frm.doc.workflow_state === "Draft") {
            frm.set_df_property("custom_reason", "read_only", 0);
        }
    }

});

function auto_fill_employee(frm) {
    // Only auto fill if it's a new document
    if (!frm.is_new()) return;

    const user_roles = frappe.user_roles;

    // Check if user is Employee role (not HR Manager or Head)
    const is_employee = user_roles.includes("Employee");
    const is_hr = user_roles.includes("HR Manager");
    const is_head = user_roles.includes("Head");

    // Only auto fill for pure Employee role
    if (is_employee && !is_hr && !is_head) {

        // Get Employee linked to current logged in user
        frappe.db.get_value(
            "Employee",
            { "user_id": frappe.session.user },
            ["name", "employee_name", "department", "designation", "company"],
            function(data) {
                if (data) {
                    // ─── Auto fill all employee fields ───
                    frm.set_value("employee", data.name);
                    frm.set_value("employee_name", data.employee_name);
                    frm.set_value("department", data.department);
                    frm.set_value("designation", data.designation);
                    frm.set_value("company", data.company);

                    // ─── Make employee field read only so cannot change ───
                    frm.set_df_property("employee", "read_only", 1);

                    frm.refresh_fields();
                } else {
                    frappe.msgprint({
                        title: __("Employee Not Found"),
                        message: __(
                            "⚠️ No Employee record linked to your account <b>{0}</b>. " +
                            "Please contact HR to link your user account."
                        ).replace("{0}", frappe.session.user),
                        indicator: "orange"
                    });
                }
            }
        );
    }
}