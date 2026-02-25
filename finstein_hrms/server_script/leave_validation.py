import frappe
from frappe import _
from datetime import datetime, date

def validate(doc, method):
    validate_leave_dates(doc)

def validate_leave_dates(doc):
    today = date.today()
    now = datetime.now()
    current_hour = now.hour  # 24hr format

    from_date = doc.from_date
    to_date = doc.to_date

    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

    # ─── Rule 1: No past dates allowed ───
    if from_date < today:
        frappe.throw(
            _("❌ Past date leave is not allowed. You can only apply for today or future dates."),
            title=_("Invalid Leave Date")
        )

    if to_date < today:
        frappe.throw(
            _("❌ To Date cannot be a past date. Please select today or a future date."),
            title=_("Invalid Leave Date")
        )

    # ─── Rule 2: Full Day leave for TODAY must be before 10:00 AM ───
    if not doc.half_day and from_date == today:
        if current_hour >= 10:
            frappe.throw(
                _(
                    "⏰ Full Day leave for today must be applied before <b>10:00 AM</b>. "
                    "Current time is {0}. Please apply for a future date."
                ).format(now.strftime("%I:%M %p")),
                title=_("Leave Application Time Restriction")
            )

    # ─── Rule 3: Half Day leave for TODAY must be before 1:00 PM ───
    if doc.half_day:
        half_day_date = doc.half_day_date

        if isinstance(half_day_date, str):
            half_day_date = datetime.strptime(half_day_date, "%Y-%m-%d").date()

        if half_day_date < today:
            frappe.throw(
                _("❌ Half Day leave cannot be applied for a past date."),
                title=_("Invalid Half Day Date")
            )

        if half_day_date == today and current_hour >= 13:
            frappe.throw(
                _(
                    "⏰ Half Day leave for today must be applied before <b>1:00 PM</b>. "
                    "Current time is {0}."
                ).format(now.strftime("%I:%M %p")),
                title=_("Half Day Leave Time Restriction")
            )

    # ─── Rule 4: Cannot apply more than 3 continuous days ───
    if not doc.half_day:
        total_days = (to_date - from_date).days + 1  # inclusive count

        if total_days > 3:
            frappe.throw(
                _(
                    "❌ You cannot apply for more than <b>3 continuous days</b> of leave. "
                    "You have selected <b>{0} days</b> ({1} to {2}). "
                    "Please split your leave or contact HR."
                ).format(
                    total_days,
                    from_date.strftime("%d-%m-%Y"),
                    to_date.strftime("%d-%m-%Y")
                ),
                title=_("Continuous Leave Limit Exceeded")
            )