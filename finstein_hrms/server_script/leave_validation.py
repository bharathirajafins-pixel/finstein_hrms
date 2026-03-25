import frappe
from frappe.utils import date_diff, flt, getdate, get_time, nowtime, today
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import (
    get_settings,
)


def validate(doc, method=None):
    """Bridge validate hook for Leave Application."""
    validate_leave_dates(doc, method)


def validate_leave_dates(doc, method=None):
    """Validate leave application against company HR policy."""
    settings = get_settings()
    max_days = settings.max_continuous_leave_days or 3
    cutoff = settings.leave_submission_cutoff_time or "17:00:00"
    half_cut = settings.half_day_cutoff_time or "12:00:00"
    allow_past = settings.allow_past_date_leave or 0

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)
    current_date = getdate(today())

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    if not allow_past and (from_date < current_date or to_date < current_date):
        frappe.throw(
            "Past date leave is not allowed. Please select today or a future date."
        )

    if not doc.half_day and from_date == current_date and nowtime() >= str(cutoff):
        frappe.throw(
            "Full-day leave for today can only be applied before "
            f"{cutoff}. Please apply for a future date."
        )

    if doc.half_day:
        half_day_date = getdate(doc.half_day_date or doc.from_date)

        if not allow_past and half_day_date < current_date:
            frappe.throw("Half-day leave cannot be applied for a past date.")

        if half_day_date == current_date and nowtime() >= str(half_cut):
            frappe.throw(
                "Half-day leave for today can only be applied before "
                f"{half_cut}."
            )

    if not doc.half_day:
        total_days = date_diff(to_date, from_date) + 1
        if total_days > max_days:
            frappe.throw(
                f"You cannot apply for more than {max_days} continuous day(s) "
                f"in one request. You selected {total_days} day(s)."
            )

    if doc.custom_from_time and doc.custom_to_time:
        if get_time(doc.custom_from_time) >= get_time(doc.custom_to_time):
            frappe.throw(
                "Leave from time must be earlier than to time. "
                "Please check the time fields and try again."
            )

    check_leave_balance(doc, settings)


def check_balance_before_submit(doc, method=None):
	"""Hook for before_submit: re-check balance at submission time."""
	settings = get_settings()
	check_leave_balance(doc, settings)


def check_leave_balance(doc, settings):
    """
    Block leave submission if requested days exceed available allocation.
    Only runs if enabled in Finstein HRMS Settings.
    """
    if not settings.enable_leave_balance_check:
        return

    allocation = frappe.db.get_value(
        "Leave Allocation",
        {
            "employee": doc.employee,
            "leave_type": doc.leave_type,
            "from_date": ("<=", doc.from_date),
            "to_date": (">=", doc.to_date),
            "docstatus": 1,
        },
        ["name", "total_leaves_allocated"],
        as_dict=True,
    )

    if not allocation:
        frappe.throw(
            f"No active leave allocation found for {doc.leave_type}. "
            "Please contact HR."
        )

    balance = get_leave_balance_on(
        doc.employee,
        doc.leave_type,
        doc.from_date,
        doc.to_date,
        consider_all_leaves_in_the_allocation_period=True,
        for_consumption=True,
    )
    available = flt(balance.get("leave_balance_for_consumption"))
    requested = flt(doc.total_leave_days or (date_diff(doc.to_date, doc.from_date) + 1))

    if requested > available:
        frappe.throw(
            f"Insufficient leave balance for {doc.leave_type}. "
            f"Available: {available} day(s). "
            f"Requested: {requested} day(s). "
            "Please adjust your leave dates or contact HR."
        )
