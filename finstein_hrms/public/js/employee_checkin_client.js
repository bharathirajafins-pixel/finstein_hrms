// ================================================================
// Client Script: Employee Checkin
// ================================================================

frappe.ui.form.on("Employee Checkin", {

    onload(frm) {
        if (frm.is_new()) {
            // Check if employee already has a record today — redirect if yes
            _check_existing_today(frm);
        }
    },

    refresh(frm) {
        _hide_fields(frm);
        frm.disable_save();
        _clear_our_buttons(frm);
        _render_buttons(frm);
        _show_one_status(frm);
    }
});


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ON NEW FORM: auto-fill employee + redirect if already checked in today
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _check_existing_today(frm) {
    frappe.call({
        method  : "frappe.client.get_list",
        args    : {
            doctype : "Employee",
            filters : { user_id: frappe.session.user },
            fields  : ["name", "employee_name"],
            limit   : 1,
        },
        callback(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint({
                    title    : __("No Employee Linked"),
                    message  : __("Your account is not linked to any Employee. Contact HR."),
                    indicator: "red"
                });
                return;
            }

            const emp      = r.message[0];
            const today    = frappe.datetime.get_today();

            // Prefer open check-in record for today, else fall back to latest record
            frappe.call({
                method  : "frappe.client.get_list",
                args    : {
                    doctype : "Employee Checkin",
                    filters : [
                        ["employee", "=", emp.name],
                        ["checkout_time", "is", "not set"],
                        ["time",     ">=", today + " 00:00:00"],
                        ["time",     "<=", today + " 23:59:59"],
                    ],
                    fields  : ["name", "checkout_time"],
                    order_by: "time desc",
                    limit   : 1,
                },
                callback(openRes) {
                    if (openRes.message && openRes.message.length) {
                        frappe.set_route("Form", "Employee Checkin", openRes.message[0].name);
                        return;
                    }

                    frappe.call({
                        method  : "frappe.client.get_list",
                        args    : {
                            doctype : "Employee Checkin",
                            filters : [
                                ["employee", "=", emp.name],
                                ["time",     ">=", today + " 00:00:00"],
                                ["time",     "<=", today + " 23:59:59"],
                            ],
                            fields  : ["name"],
                            order_by: "time desc",
                            limit   : 1,
                        },
                        callback(latestRes) {
                            if (latestRes.message && latestRes.message.length) {
                                frappe.set_route("Form", "Employee Checkin", latestRes.message[0].name);
                            } else {
                                frm.set_value("employee",      emp.name);
                                frm.set_value("employee_name", emp.employee_name);
                                frm.set_df_property("employee",      "read_only", 1);
                                frm.set_df_property("employee_name", "read_only", 1);
                                frm.refresh_fields();
                            }
                        }
                    });
                }
            });
        }
    });
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// RENDER BUTTONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _render_buttons(frm) {
    const doc          = frm.doc;
    const onBreak      = doc.break_start && !doc.break_end;

    if (doc.checkout_time) {
        // Complete — lock
        frm.set_read_only();
        return;
    }

    if (!doc.time) {
        // Not checked in yet
        _btn(frm, "Check In", "btn-success", () => _do_checkin(frm));
        return;
    }

    // Checked in
    if (onBreak) {
        _btn(frm, "Permission Check-In", "btn-success", () => _do_break_end(frm));
        return;
    }

    _btn(frm, "Check Out", "btn-danger", () => _do_checkout(frm, false));
    _btn(frm, "Permission Checkout", "btn-warning", () => _do_break_start(frm));
    _btn(frm, "Force Checkout", "btn-warning", () => _do_checkout(frm, true));
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SINGLE STATUS — called once, no duplicates
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _show_one_status(frm) {
    frm.dashboard.reset();   // clear ALL previous indicators/comments

    const doc     = frm.doc;
    const onBreak = doc.break_start && !doc.break_end;

    if (!doc.time) {
        frm.dashboard.add_indicator(__("Not Checked In"), "gray");

    } else if (doc.checkout_time) {
        const status = doc.attendance_status || "";
        const color  = status === "Present" ? "green" : status === "Half Day" ? "orange" : "red";
        frm.dashboard.add_indicator(
            __("{0}  |  {1} hrs worked", [status, doc.working_hours || 0]),
            color
        );

    } else if (onBreak) {
        frm.dashboard.add_indicator(
            __("On permission break since {0}. Click Permission Check-In to resume work.", [frappe.datetime.str_to_user(doc.break_start)]),
            "orange"
        );

    } else {
        const elapsed = _elapsed_hrs(doc.time).toFixed(1);
        const remaining = Math.max(8 - parseFloat(elapsed), 0).toFixed(1);
        frm.dashboard.add_indicator(
            __("Checked In ✅  {0}  |  {1} hrs elapsed  |  {2} hrs to checkout",
               [frappe.datetime.str_to_user(doc.time), elapsed, remaining]),
            "green"
        );
    }
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// HIDE unwanted fields — by fieldname AND by section label
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _hide_fields(frm) {
    const HIDE = [
        "device_id", "skip_auto_attendance", "shift", "attendance",
        "late_entry", "early_exit", "remarks",
        "sb_shift_details", "sb_attendance_details",
        "column_break_6", "section_break_7", "section_break_9", "column_break_8",
    ];
    HIDE.forEach(fn => {
        if (frm.fields_dict[fn]) frm.set_df_property(fn, "hidden", 1);
    });

    // Remove verbose helper text from shown fields
    ["time", "checkout_time", "working_hours", "attendance_status", "checkout_type", "log_type", "log_type_out"]
        .forEach(fn => {
            if (frm.fields_dict[fn]) frm.set_df_property(fn, "description", "");
        });

    // Keep checkout-only fields hidden until employee checks out
    const hasCheckin = !!frm.doc.time;
    const hasCheckout = !!frm.doc.checkout_time;

    // Always show IN log type once check-in exists
    if (frm.fields_dict.log_type) {
        frm.set_df_property("log_type", "hidden", hasCheckin ? 0 : 1);
    }

    // Show OUT-side fields only after checkout is done
    ["checkout_time", "log_type_out", "checkout_type", "break_start", "break_end", "break_hours"]
        .forEach(fn => {
            if (frm.fields_dict[fn]) frm.set_df_property(fn, "hidden", hasCheckout ? 0 : 1);
        });

    // Hide standard sections by label
    frm.fields.forEach(f => {
        const lbl = (f.df.label || "").toLowerCase();
        if (f.df.fieldtype === "Section Break" &&
            (lbl === "shift timings" || lbl === "work summary" || lbl === "attendance details")) {
            frm.set_df_property(f.df.fieldname, "hidden", 1);
        }
    });

    // Lock employee fields
    if (frm.doc.employee) {
        frm.set_df_property("employee",      "read_only", 1);
        frm.set_df_property("employee_name", "read_only", 1);
    }

    frm.refresh_fields();
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ACTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _do_checkin(frm) {
    if (!frm.doc.employee) {
        frappe.throw(__("Employee not linked. Contact HR.")); return;
    }
    const now = frappe.datetime.now_datetime();
    frm.set_value("time",     now);
    frm.set_value("log_type", "IN");
    frm.save("Save").then(() => {
        frappe.show_alert({ message: __("✅ Checked In at {0}", [frappe.datetime.str_to_user(now)]), indicator: "green" }, 5);
        frm.refresh();
    });
}

function _do_checkout(frm, isForce) {
    const name = frm.doc.employee_name || frm.doc.employee;
    const msg  = isForce
        ? __("Force Checkout for <b>{0}</b>?<br>Status will be calculated based on worked hours.", [name])
        : __("Confirm Check Out for <b>{0}</b>?", [name]);

    frappe.confirm(msg, () => {
        const now      = frappe.datetime.now_datetime();
        const totalHrs = _elapsed_hrs(frm.doc.time);
        const breakHrs = parseFloat(frm.doc.break_hours || 0);
        const netHrs   = parseFloat(Math.max(totalHrs - breakHrs, 0).toFixed(2));

        if (!isForce && netHrs < 8) {
            frappe.msgprint({
                title: __("Checkout Not Allowed Yet"),
                indicator: "orange",
                message: __("Minimum 8 working hours required. Current: <b>{0} hrs</b>.", [netHrs])
            });
            return;
        }

        let status = "Absent";
        if      (netHrs >= 8) status = "Present";
        else if (netHrs >= 4) status = "Half Day";

        frm.set_value("checkout_time", now);
        frm.set_value("log_type_out",  isForce ? "FORCE OUT" : "OUT");
        _safe(frm, "checkout_type",     isForce ? "Force" : "Normal");
        _safe(frm, "working_hours",     netHrs);
        _safe(frm, "attendance_status", status);

        frm.save("Save").then(() => {
            const color = status === "Present" ? "green" : status === "Half Day" ? "orange" : "red";
            frappe.show_alert({
                message  : __("{0}  |  {1} hrs  |  {2}",
                    [isForce ? "⚡ Force Checkout" : "🔴 Checked Out", netHrs, status]),
                indicator: color
            }, 7);
            frm.refresh();
        });
    });
}

function _do_break_start(frm) {
    frappe.confirm(
        __("Permission Checkout for <b>{0}</b>? Break time will NOT count as working hours.", [frm.doc.employee_name]),
        () => {
            const now = frappe.datetime.now_datetime();
            _safe(frm, "break_start", now);
            // Reset break_end so form clearly enters "on break" state.
            _safe(frm, "break_end", null);
            frm.save("Save").then(() => {
                frappe.show_alert({ message: __("🟡 Break started at {0}", [frappe.datetime.str_to_user(now)]), indicator: "orange" }, 5);
                frm.refresh();
            });
        }
    );
}

function _do_break_end(frm) {
    frappe.confirm(
        __("Permission Check-In and resume work for <b>{0}</b>?", [frm.doc.employee_name]),
        () => {
            const now      = frappe.datetime.now_datetime();
            const bs       = frappe.datetime.str_to_obj(frm.doc.break_start);
            const be       = frappe.datetime.str_to_obj(now);
            const currentBreak = parseFloat(frm.doc.break_hours || 0);
            const thisBreak    = parseFloat(((be - bs) / (1000 * 60 * 60)).toFixed(2));
            const breakHrs     = parseFloat((currentBreak + thisBreak).toFixed(2));
            _safe(frm, "break_end",   now);
            _safe(frm, "break_hours", breakHrs);
            frm.save("Save").then(() => {
                frappe.show_alert({ message: __("✅ Work resumed. Total break: {0} hrs", [breakHrs]), indicator: "green" }, 5);
                frm.refresh();
            });
        }
    );
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function _elapsed_hrs(timeStr) {
    if (!timeStr) return 0;
    return (new Date() - frappe.datetime.str_to_obj(timeStr)) / (1000 * 60 * 60);
}

function _safe(frm, fieldname, value) {
    if (frm.fields_dict[fieldname]) frm.set_value(fieldname, value);
}

function _is_privileged() {
    return frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager");
}

function _btn(frm, label, cls, handler) {
    frm.add_custom_button(__(label), handler)
        .removeClass("btn-default btn-primary btn-success btn-danger btn-warning")
        .addClass("btn-default")
        .css({
            "background-color": "#111111",
            "border-color": "#111111",
            "color": "#ffffff",
            "font-weight": "600",
            "padding": "6px 22px",
            "font-size": "13px",
            "margin-left": "6px",
        });
}

function _clear_our_buttons(frm) {
    [
        "Check In",
        "Check Out",
        "Force Checkout",
        "Permission Checkout",
        "Permission Check-In",
        // backward compatibility for older labels
        "  Check In",
        "  Check Out",
        "  Force Check Out ",
        " Force Check In ",
        "⚡  Force Checkout",
    ].forEach((label) => frm.remove_custom_button(__(label)));
}
