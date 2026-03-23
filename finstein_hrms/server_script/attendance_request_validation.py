from datetime import timedelta

import frappe
from frappe.utils import add_months, add_days, getdate, today

from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import (
    get_settings,
)


def validate(doc, method=None):
    """Bridge validate hook for Attendance Request."""
    validate_attendance_request(doc, method)


def validate_attendance_request(doc, method=None):
    """Validate attendance correction request against policy."""
    settings = get_settings()
    max_req = settings.max_attendance_requests_per_month or 5
    curr_only = settings.restrict_to_current_month
    allowed_raw = settings.allowed_attendance_statuses or ""
    allowed = [status.strip() for status in allowed_raw.splitlines() if status.strip()]

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)
    current_date = getdate(today())

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    check_attendance_not_locked(doc)

    if from_date >= current_date or to_date >= current_date:
        frappe.throw(
            "Attendance Request is allowed only for past dates. "
            "Today and future dates are not permitted."
        )

    if curr_only and (
        from_date.month != current_date.month
        or from_date.year != current_date.year
        or to_date.month != current_date.month
        or to_date.year != current_date.year
    ):
        frappe.throw(
            "Attendance Request is restricted to the current month only. "
            "Please contact HR for older date corrections."
        )

    month_start = current_date.replace(day=1)
    month_end = add_days(add_months(month_start, 1), -1)

    existing_requests = frappe.db.count(
        "Attendance Request",
        filters=[
            ["employee", "=", doc.employee],
            ["from_date", ">=", month_start],
            ["from_date", "<=", month_end],
            ["docstatus", "!=", 2],
            ["name", "!=", doc.name],
        ],
    )

    if existing_requests >= max_req:
        frappe.throw(
            f"You have already submitted {existing_requests} attendance request(s) "
            f"this month. Maximum allowed is {max_req}."
        )

    # Some deployments use attendance_type on the request itself.
    request_status = getattr(doc, "attendance_type", None)
    if request_status:
        if allowed and request_status not in allowed:
            allowed_display = ", ".join(allowed)
            frappe.throw(
                f"Attendance Request is only allowed for these statuses: "
                f"{allowed_display}. Found '{request_status}'."
            )
        return

    for check_date in _date_range(from_date, to_date):
        attendance = frappe.db.get_value(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": check_date,
                "docstatus": 1,
            },
            ["status", "name", "custom_locked"],
            as_dict=True,
        )

        if not attendance:
            frappe.throw(
                f"No submitted Attendance record was found for {check_date}. "
                "Please contact HR."
            )

        if attendance.custom_locked:
            frappe.throw(
                "Attendance for this date is locked because payroll has already "
                "been processed for this period. Please contact HR if a "
                "correction is needed."
            )

        if allowed and attendance.status not in allowed:
            allowed_display = ", ".join(allowed)
            frappe.throw(
                f"Attendance Request is only allowed for these statuses: "
                f"{allowed_display}. Found '{attendance.status}' on {check_date}."
            )


def check_attendance_not_locked(doc):
    """
    Block attendance correction requests if any date in the request range is locked.
    """
    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    for check_date in _date_range(from_date, to_date):
        locked = frappe.db.get_value(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": check_date,
            },
            "custom_locked",
        )
        if locked:
            frappe.throw(
                "Attendance for this date is locked because payroll has already "
                "been processed for this period. Please contact HR if a "
                "correction is needed."
            )


def _date_range(start_date, end_date):
    """Yield all dates between start_date and end_date (inclusive)."""
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
