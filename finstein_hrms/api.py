from datetime import time

import frappe
from frappe.utils import nowdate, now_datetime

from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import (
    get_settings,
)


DEFAULT_TIME_WINDOWS = {
    "Breakfast": {"start": time(9, 0), "end": time(11, 0)},
    "Lunch": {"start": time(12, 30), "end": time(15, 0)},
    "Dinner": {"start": time(19, 0), "end": time(22, 0)},
}
TIME_WINDOWS = DEFAULT_TIME_WINDOWS


def _get_time_windows():
    """Build meal windows from settings with fallback defaults."""
    try:
        settings = get_settings()
    except Exception:
        return DEFAULT_TIME_WINDOWS

    return {
        "Breakfast": {
            "start": frappe.utils.get_time(settings.meal_breakfast_open or "09:00:00"),
            "end": frappe.utils.get_time(settings.meal_breakfast_close or "11:00:00"),
        },
        "Lunch": {
            "start": frappe.utils.get_time(settings.meal_lunch_open or "12:30:00"),
            "end": frappe.utils.get_time(settings.meal_lunch_close or "15:00:00"),
        },
        "Dinner": {
            "start": frappe.utils.get_time(settings.meal_dinner_open or "19:00:00"),
            "end": frappe.utils.get_time(settings.meal_dinner_close or "22:00:00"),
        },
    }


def _window_str(food_type):
    """Return display string for one meal window."""
    windows = _get_time_windows()
    window = windows.get(food_type)
    if not window:
        return ""
    return f"{window['start'].strftime('%I:%M %p')} - {window['end'].strftime('%I:%M %p')}"


@frappe.whitelist(allow_guest=False)
def scan_food_qr(qr_data):
    """
    Validate a meal QR scan and mark employee meal as consumed.

    Accepts either full encoded QR payload (FQR|...) or a direct Food QR docname.
    """
    employee = frappe.session.user
    today = nowdate()
    now_time = now_datetime().time()

    if not qr_data:
        frappe.throw("QR data is missing.")

    qr_doc = None
    qr_food_type = None

    qr_data_text = str(qr_data).strip()

    if qr_data_text.startswith("FQR|"):
        parts = qr_data_text.split("|")
        if len(parts) != 4:
            frappe.throw("Invalid QR code. Please scan the correct meal QR.")

        qr_food_type = parts[2]
        qr_name = frappe.db.get_value("Food QR", {"qr_data": qr_data_text}, "name")
        if not qr_name:
            frappe.throw("QR code not recognised. Please try again.")

        qr_doc = frappe.get_doc("Food QR", qr_name)
    else:
        qr_doc = frappe.get_doc("Food QR", qr_data_text)
        qr_food_type = getattr(qr_doc, "food_type", None) or getattr(qr_doc, "meal_type", None)

    if not qr_food_type:
        frappe.throw("Meal type is missing on the QR record.")

    status = (qr_doc.status or "").strip()

    if status == "Consumed":
        frappe.throw("This QR has already been consumed.")

    if status in ("Pending", "Scheduled"):
        frappe.throw(f"{qr_food_type} QR is not active yet.")

    if status in ("Cancelled", "Closed"):
        frappe.throw(f"{qr_food_type} session is closed or cancelled.")

    if status != "Active":
        frappe.throw("This QR is not in an active state for scanning.")

    qr_employee = getattr(qr_doc, "employee", None)
    if qr_employee and qr_employee != employee:
        frappe.throw("This QR is assigned to another employee.")

    windows = _get_time_windows()
    window = windows.get(qr_food_type)

    if not window:
        frappe.throw(f"Unknown food type: {qr_food_type}")

    if not (window["start"] <= now_time <= window["end"]):
        frappe.throw(
            f"Outside serving window. {qr_food_type} is only available {_window_str(qr_food_type)}."
        )

    food_count_name = frappe.db.get_value(
        "Food Count",
        {"user": employee, "order_date": today},
        "name",
    )

    if not food_count_name:
        frappe.throw(
            "No order found for you today. You must place your order before collection."
        )

    food_count = frappe.get_doc("Food Count", food_count_name)

    field_map = {
        "Breakfast": ("breakfast_selected", "breakfast_status"),
        "Lunch": ("lunch_selected", "lunch_status"),
        "Dinner": ("dinner_selected", "dinner_status"),
    }

    if qr_food_type not in field_map:
        frappe.throw(f"Unsupported meal type: {qr_food_type}")

    selected_field, status_field = field_map[qr_food_type]
    is_selected = int(getattr(food_count, selected_field, 0) or 0)
    current_status = getattr(food_count, status_field, "")

    if not is_selected:
        frappe.throw(
            f"You did not order {qr_food_type} for today. Only ordered meals can be collected."
        )

    if current_status == "Consumed":
        frappe.throw(f"You already collected your {qr_food_type} today.")

    if current_status == "Cancelled":
        frappe.throw(f"Your {qr_food_type} order was cancelled.")

    frappe.db.set_value("Food Count", food_count_name, status_field, "Consumed")
    new_count = int(qr_doc.consumed_count or 0) + 1
    frappe.db.set_value("Food QR", qr_doc.name, "consumed_count", new_count)
    frappe.db.commit()

    return {
        "success": True,
        "food_type": qr_food_type,
        "food_item": qr_doc.food_item,
        "consumed_count": new_count,
        "put_count": qr_doc.food_put_count,
        "message": (
            f"Enjoy your {qr_food_type}. {qr_doc.food_item} collected. "
            f"({new_count}/{qr_doc.food_put_count} served today)"
        ),
    }


@frappe.whitelist(allow_guest=False)
def get_todays_food_qr():
    """Provider page helper: list today's meal QR slots with counts."""
    return frappe.get_list(
        "Food QR",
        filters=[["date", "=", nowdate()]],
        fields=[
            "name",
            "date",
            "day",
            "food_type",
            "food_item",
            "serving_time",
            "window_start",
            "window_end",
            "status",
            "food_put_count",
            "consumed_count",
            "qr_data",
            "qr_image_url",
            "vendor",
        ],
        order_by="serving_time asc",
    )


@frappe.whitelist(allow_guest=False)
def get_my_order_status():
    """Return current user's meal order statuses for today."""
    name = frappe.db.get_value(
        "Food Count",
        {"user": frappe.session.user, "order_date": nowdate()},
        "name",
    )

    if not name:
        return None

    doc = frappe.get_doc("Food Count", name)
    return {
        "breakfast": doc.breakfast,
        "breakfast_status": doc.breakfast_status,
        "lunch": doc.lunch,
        "lunch_status": doc.lunch_status,
        "dinner": doc.dinner,
        "dinner_status": doc.dinner_status,
    }


@frappe.whitelist()
def withdraw_leave_application(docname):
    """
    Allow an employee to withdraw their own pending leave application.
    """
    doc = frappe.get_doc("Leave Application", docname)

    if doc.owner != frappe.session.user:
        frappe.throw("You can only withdraw your own leave applications.")

    if doc.workflow_state not in ["Pending", "Pending HR Approve"]:
        frappe.throw(
            f"This application cannot be withdrawn at the '{doc.workflow_state}' stage. "
            "Please contact HR."
        )

    doc.workflow_state = "Draft"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.logger().info(f"[LeaveWithdraw] {frappe.session.user} withdrew {docname}")

    return {"status": "withdrawn", "docname": docname}


@frappe.whitelist()
def is_employee_team_leader(employee):
    """
    Return whether the selected employee's linked user has the Team Leader role.
    """
    if not employee:
        return {"is_team_leader": False}

    employee_user = frappe.db.get_value("Employee", employee, "user_id")
    if not employee_user:
        return {"is_team_leader": False}

    return {
        "is_team_leader": "Team Leader" in frappe.get_roles(employee_user),
        "user_id": employee_user,
    }


@frappe.whitelist()
def cancel_meal_order(qr_name):
    """
    Cancel current user's meal order for a QR slot before serving window opens.
    """
    settings = get_settings()
    if not settings.enable_meal_cancellation:
        frappe.throw(
            "Meal order cancellation is not enabled. Please contact HR."
        )

    qr_doc = frappe.get_doc("Food QR", qr_name)

    if getattr(qr_doc, "employee", None) and qr_doc.employee != frappe.session.user:
        frappe.throw("You can only cancel your own meal orders.")

    if qr_doc.status not in ["Pending", "Scheduled"]:
        frappe.throw(
            f"This order cannot be cancelled. Current status: {qr_doc.status}. "
            "Orders can only be cancelled before the window opens."
        )

    meal_type = getattr(qr_doc, "food_type", None) or getattr(qr_doc, "meal_type", None)
    if meal_type not in ("Breakfast", "Lunch", "Dinner"):
        frappe.throw("Invalid meal type for cancellation.")

    food_count_name = frappe.db.get_value(
        "Food Count",
        {"user": frappe.session.user, "order_date": qr_doc.date},
        "name",
    )
    if not food_count_name:
        frappe.throw("No meal order found for your account on this date.")

    food_count = frappe.get_doc("Food Count", food_count_name)
    field_map = {
        "Breakfast": ("breakfast_selected", "breakfast_status"),
        "Lunch": ("lunch_selected", "lunch_status"),
        "Dinner": ("dinner_selected", "dinner_status"),
    }

    selected_field, status_field = field_map[meal_type]

    if not int(getattr(food_count, selected_field, 0) or 0):
        frappe.throw("You do not have an active order for this meal.")

    current_status = getattr(food_count, status_field, "")
    if current_status not in ("", "Pending"):
        frappe.throw(
            f"This order cannot be cancelled. Current status: {current_status}."
        )

    setattr(food_count, selected_field, 0)
    setattr(food_count, status_field, "Cancelled")
    food_count.save(ignore_permissions=True)

    if qr_doc.food_put_count:
        frappe.db.set_value(
            "Food QR",
            qr_doc.name,
            "food_put_count",
            max(int(qr_doc.food_put_count) - 1, 0),
        )

    frappe.db.commit()
    frappe.logger().info(f"[MealCancel] {frappe.session.user} cancelled {qr_name}")

    return {"status": "cancelled", "qr_name": qr_name}


@frappe.whitelist()
def check_payroll_readiness(start_date, end_date):
    """
    Return payroll readiness checklist for the selected date range.
    """
    settings = get_settings()
    if not settings.enable_payroll_readiness_check:
        return {"enabled": False}

    pending_leaves = frappe.db.count(
        "Leave Application",
        {
            "workflow_state": "Pending HR Approve",
            "from_date": (">=", start_date),
            "to_date": ("<=", end_date),
        },
    )

    pending_attendance = frappe.db.count(
        "Attendance Request",
        {
            "workflow_state": "Pending HR Approve",
            "from_date": (">=", start_date),
            "to_date": ("<=", end_date),
        },
    )

    unsynced_checkins = frappe.db.count(
        "Employee Checkin",
        {
            "attendance": ("is", "not set"),
            "time": ("between", [start_date, end_date]),
        },
    )

    is_ready = pending_leaves == 0 and pending_attendance == 0 and unsynced_checkins == 0

    return {
        "enabled": True,
        "pending_leave_approvals": pending_leaves,
        "pending_attendance_corrections": pending_attendance,
        "unsynced_checkins": unsynced_checkins,
        "ready": is_ready,
        "start_date": start_date,
        "end_date": end_date,
    }
