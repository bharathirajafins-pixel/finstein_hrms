import frappe
from frappe import _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def validate(doc, method=None):
    validate_attendance_request(doc)

def validate_attendance_request(doc, method=None):
    today = date.today()

    from_date = doc.from_date
    to_date = doc.to_date

    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

    # ─── Rule 1: Cannot request for Current Date or Future Dates ───
    if from_date >= today:
        frappe.throw(
            _(
                "❌ You cannot request attendance for <b>today or future dates</b>. "
                "Only past dates are allowed."
            ),
            title=_("Invalid Attendance Request Date")
        )

    if to_date >= today:
        frappe.throw(
            _(
                "❌ To Date cannot be today or a future date. "
                "Please select a past date."
            ),
            title=_("Invalid Attendance Request Date")
        )

    # ─── Rule 2: Only Current Month Requests Allowed ───
    current_month = today.month
    current_year = today.year

    if from_date.month != current_month or from_date.year != current_year:
        frappe.throw(
            _(
                "❌ You can only request attendance for the <b>current month ({0})</b>. "
                "Requests for past months are not allowed."
            ).format(today.strftime("%B %Y")),
            title=_("Past Month Request Not Allowed")
        )

    if to_date.month != current_month or to_date.year != current_year:
        frappe.throw(
            _(
                "❌ To Date must be within the <b>current month ({0})</b>. "
                "Requests for past months are not allowed."
            ).format(today.strftime("%B %Y")),
            title=_("Past Month Request Not Allowed")
        )

    # ─── Rule 3: Only 5 Attendance Requests Per Month ───
    month_start = today.replace(day=1)
    month_end = (today.replace(day=1) + relativedelta(months=1))

    existing_requests = frappe.db.count("Attendance Request", filters={
        "employee": doc.employee,
        "from_date": [">=", month_start.strftime("%Y-%m-%d")],
        "to_date": ["<", month_end.strftime("%Y-%m-%d")],
        "docstatus": ["!=", 2],  # exclude cancelled
        "name": ["!=", doc.name]  # exclude current doc on edit
    })

    if existing_requests >= 5:
        frappe.throw(
            _(
                "❌ You have already submitted <b>{0} Attendance Requests</b> this month. "
                "Maximum <b>5 requests per month</b> are allowed. "
                "Please contact HR for further assistance."
            ).format(existing_requests),
            title=_("Monthly Attendance Request Limit Exceeded")
        )

    # ─── Rule 4: Only Allow Request for Leave / Off Day / Absent Status ───
    allowed_statuses = ["On Leave", "Half Day", "Absent"]

    # Get all dates in the range
    date_range = []
    current_date = from_date
    while current_date <= to_date:
        date_range.append(current_date)
        current_date = current_date + frappe.utils.datetime.timedelta(days=1)

    for check_date in date_range:
        attendance = frappe.db.get_value(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": check_date.strftime("%Y-%m-%d"),
                "docstatus": 1  # submitted attendance only
            },
            ["status", "name"],
            as_dict=True
        )

        if not attendance:
            frappe.throw(
                _(
                    "❌ No attendance record found for <b>{0}</b> on <b>{1}</b>. "
                    "You can only request for dates with existing attendance records."
                ).format(
                    doc.employee,
                    check_date.strftime("%d-%m-%Y")
                ),
                title=_("No Attendance Record Found")
            )

        if attendance.status not in allowed_statuses:
            frappe.throw(
                _(
                    "❌ Attendance request is only allowed for days marked as "
                    "<b>On Leave / Half Day / Absent</b>. "
                    "Your status on <b>{0}</b> is <b>{1}</b>. "
                    "You cannot request attendance for this date."
                ).format(
                    check_date.strftime("%d-%m-%Y"),
                    attendance.status
                ),
                title=_("Invalid Attendance Status for Request")
            )