"""
Server Validation: Employee Checkin
File: finstein_hrms/server_script/checkin_validation.py
Hook: before_save
"""
import frappe
from frappe import _
from frappe.utils import get_datetime, time_diff_in_hours, getdate


def validate_checkin(doc, method=None):
    _mandatory(doc)
    _no_duplicate(doc)
    _checkout_order(doc)
    _min_8hrs(doc)
    _calc_hours(doc)
    _set_status(doc)


def sync_attendance_from_checkin(doc, method=None):
    """Create or update Attendance once check-out is completed."""
    if not (doc.employee and doc.time and doc.checkout_time):
        return

    attendance_date = getdate(doc.time)
    status = (doc.attendance_status or "").strip() or "Absent"

    existing = frappe.db.exists(
        "Attendance",
        {"employee": doc.employee, "attendance_date": attendance_date, "docstatus": ("!=", 2)},
    )

    if existing:
        att = frappe.get_doc("Attendance", existing)
        att.status = status
        att.flags.ignore_validate = True
        att.save(ignore_permissions=True)
        if att.docstatus == 0:
            att.submit()
        return

    att = frappe.new_doc("Attendance")
    att.employee = doc.employee
    att.attendance_date = attendance_date
    att.status = status
    att.flags.ignore_validate = True
    att.insert(ignore_permissions=True)
    att.submit()


def _mandatory(doc):
    if not doc.employee:
        frappe.throw(_("Employee is mandatory."))
    if not doc.time:
        frappe.throw(_("Check-In Time is mandatory."))


def _no_duplicate(doc):
    date = getdate(doc.time)
    rows = frappe.get_all(
        "Employee Checkin",
        filters={"employee": doc.employee, "name": ("!=", doc.name)},
        fields=["name", "time"],
    )
    for r in rows:
        if r.time and getdate(r.time) == date:
            frappe.throw(_(
                "Check-In already exists for <b>{0}</b> on <b>{1}</b>. "
                "Please open the existing record: <b>{2}</b>"
            ).format(doc.employee_name or doc.employee, date, r.name))


def _checkout_order(doc):
    if doc.checkout_time and doc.time:
        if get_datetime(doc.checkout_time) <= get_datetime(doc.time):
            frappe.throw(_("Check-Out Time must be after Check-In Time."))


def _min_8hrs(doc):
    if not (doc.checkout_time and doc.time):
        return
    is_privileged = any(r in frappe.get_roles() for r in ["HR Manager", "System Manager"])
    is_force      = (getattr(doc, "checkout_type", "") == "Force")
    if is_force or is_privileged:
        return
    total = time_diff_in_hours(get_datetime(doc.checkout_time), get_datetime(doc.time))
    brk   = float(getattr(doc, "break_hours", 0) or 0)
    hrs   = max(total - brk, 0)
    if hrs < 8:
        frappe.throw(_(
            "Minimum 8 working hours required. Current: <b>{0} hrs</b>."
        ).format(round(hrs, 2)))


def _calc_hours(doc):
    if doc.time and doc.checkout_time:
        total = time_diff_in_hours(get_datetime(doc.checkout_time), get_datetime(doc.time))
        brk   = float(getattr(doc, "break_hours", 0) or 0)
        doc.working_hours = round(max(total - brk, 0), 2)
    else:
        doc.working_hours = None


def _set_status(doc):
    if not doc.checkout_time:
        return
    hrs = float(doc.working_hours or 0)
    if   hrs >= 8: doc.attendance_status = "Present"
    elif hrs >= 4: doc.attendance_status = "Half Day"
    else:          doc.attendance_status = "Absent"
