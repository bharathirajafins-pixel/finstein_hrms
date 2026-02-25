# finstein_hrms/server_script/attendances_request.py

import frappe
from frappe.utils import getdate, today, add_days, add_months, get_datetime

def validate(doc, method):
    # Get request date
    request_date = getdate(doc.from_date)

    if not request_date:
        frappe.throw("Attendance Request Date is required.")

    current_date = getdate(today())

    # -----------------------------------
    # 🚫 Block Today & Future Date Requests
    # -----------------------------------
    if request_date >= current_date:
        frappe.throw(
            "Attendance Request is only allowed for Past dates. Today and Future dates are not permitted."
        )

    # -----------------------------------
    # 1️⃣ Calculate Payroll Cycle (26 → 25)
    # -----------------------------------
    if current_date.day >= 26:
        cycle_start = current_date.replace(day=26)
        next_month = add_months(cycle_start, 1)
        cycle_end = next_month.replace(day=25)
    else:
        first_day = current_date.replace(day=1)
        last_month = add_days(first_day, -1)
        cycle_start = last_month.replace(day=26)
        cycle_end = current_date.replace(day=25)

    # -----------------------------------
    # 2️⃣ Validate Date Inside Payroll Cycle
    # -----------------------------------
    if not (cycle_start <= request_date <= cycle_end):
        frappe.throw(
            f"Attendance Request allowed only between {cycle_start} and {cycle_end}."
        )

    # -----------------------------------
    # 3️⃣ Only validate on Draft (docstatus = 0)
    # -----------------------------------
    if doc.docstatus == 0:

        # -----------------------------------
        # 4️⃣ Count Existing Requested Days (Exclude current doc)
        # -----------------------------------
        existing_days = frappe.db.sql("""
            SELECT SUM(DATEDIFF(to_date, from_date) + 1)
            FROM `tabAttendance Request`
            WHERE employee = %s
            AND docstatus != 2
            AND name != %s
            AND from_date >= %s
            AND to_date <= %s
        """, (doc.employee, doc.name, cycle_start, cycle_end))[0][0] or 0

        current_request_days = (
            getdate(doc.to_date) - getdate(doc.from_date)
        ).days + 1

        if existing_days + current_request_days > 5:
            frappe.throw(
                "You can submit Attendance Request only for maximum 5 days in one payroll cycle (26 to 25)."
            )

        # -----------------------------------
        # 5️⃣ Prevent Request If Check-in Exists
        # -----------------------------------
        from_datetime = get_datetime(str(getdate(doc.from_date)) + " 00:00:00")
        to_datetime = get_datetime(str(getdate(doc.to_date)) + " 23:59:59")

        checkins = frappe.db.exists("Employee Checkin", {
            "employee": doc.employee,
            "time": ["between", [from_datetime, to_datetime]]
        })

        if checkins:
            frappe.throw(
                "Attendance Request not allowed. Employee has already done Check-in / Check-out for the selected date(s)."
            )