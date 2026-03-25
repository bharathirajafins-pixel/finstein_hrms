import uuid
from datetime import time

import frappe
from frappe.utils import getdate, nowdate, get_time

from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import (
    get_settings,
)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _load_settings():
    """Safely load settings with a sensible fallback during setup/migration."""
    try:
        return get_settings()
    except (frappe.DoesNotExistError, frappe.ValidationError):
        frappe.logger().warning("[MealSystem] Finstein HRMS Settings not available. Using defaults.")
        return None


def get_meal_windows():
    """Read meal window times from Finstein HRMS Settings."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        return None

    breakfast_open = str(settings.meal_breakfast_open) if settings and settings.meal_breakfast_open else "09:00:00"
    breakfast_close = str(settings.meal_breakfast_close) if settings and settings.meal_breakfast_close else "11:00:00"
    lunch_open = str(settings.meal_lunch_open) if settings and settings.meal_lunch_open else "12:30:00"
    lunch_close = str(settings.meal_lunch_close) if settings and settings.meal_lunch_close else "15:00:00"
    dinner_open = str(settings.meal_dinner_open) if settings and settings.meal_dinner_open else "19:00:00"
    dinner_close = str(settings.meal_dinner_close) if settings and settings.meal_dinner_close else "22:00:00"

    return {
        "Breakfast": {
            "open": breakfast_open,
            "close": breakfast_close,
        },
        "Lunch": {
            "open": lunch_open,
            "close": lunch_close,
        },
        "Dinner": {
            "open": dinner_open,
            "close": dinner_close,
        },
    }


def _get_order_count(order_date, food_type):
    """Return selected order count for a meal type on a date."""
    field_map = {
        "Breakfast": "breakfast_selected",
        "Lunch": "lunch_selected",
        "Dinner": "dinner_selected",
    }
    db_field = field_map.get(food_type)
    if not db_field:
        return 0
    return frappe.db.count(
        "Food Count",
        filters=[["order_date", "=", order_date], [db_field, "=", 1]],
    )


def _build_qr_payload(target_date, day_name, food_type, food_item, put_count):
    """Build payload for Food QR insert/update."""
    windows = get_meal_windows() or {}
    slot = windows.get(food_type) or {}
    start_time = slot.get("open", "09:00:00")
    end_time = slot.get("close", "11:00:00")

    unique_id = uuid.uuid4().hex[:10].upper()
    qr_data = f"FQR|{target_date}|{food_type}|{unique_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_data}"

    open_display = get_time(start_time).strftime("%I:%M %p")
    close_display = get_time(end_time).strftime("%I:%M %p")

    return {
        "date": target_date,
        "day": day_name,
        "food_type": food_type,
        "food_item": food_item,
        "serving_time": start_time,
        "window_start": start_time,
        "window_end": end_time,
        "status": "Scheduled",
        "food_put_count": put_count,
        "consumed_count": 0,
        "qr_data": qr_data,
        "qr_image_url": qr_url,
        "qr_display": (
            f'<div style="text-align:center;padding:20px;">'
            f'<img src="{qr_url}" style="width:240px;height:240px;'
            f'border-radius:12px;border:3px solid #f39c12;">'
            f'<p style="margin-top:10px;font-weight:700;font-size:16px;">'
            f'{food_type} - {food_item}</p>'
            f'<p style="color:#888;font-size:12px;">{day_name}, {target_date}</p>'
            f'<p style="color:#aaa;font-size:11px;">Window: '
            f"{open_display} - {close_display}</p>"
            f"</div>"
        ),
    }


def generate_food_qr_for_date(target_date, food_type=None, force_regenerate=False):
    """
    Generate Food QR records for a date.
    Optionally limit generation to one meal type.
    """
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return []

    target_date = str(target_date)
    target_day_name = DAY_NAMES[getdate(target_date).weekday()]

    menu_list = frappe.get_list(
        "Food Menu Item",
        filters=[["day", "=", target_day_name], ["available", "=", 1]],
        fields=["name", "breakfast_item", "lunch_item", "dinner_item"],
        limit=1,
    )
    if not menu_list:
        frappe.throw(f"No available menu found for {target_day_name}.")

    menu = menu_list[0]
    meal_items = {
        "Breakfast": menu.get("breakfast_item"),
        "Lunch": menu.get("lunch_item"),
        "Dinner": menu.get("dinner_item"),
    }

    if food_type:
        if food_type not in meal_items:
            frappe.throw(f"Invalid food type: {food_type}")
        meal_items = {food_type: meal_items.get(food_type)}

    created_or_updated = []

    for meal_type, food_item in meal_items.items():
        if not food_item:
            continue

        put_count = _get_order_count(target_date, meal_type)
        existing_name = frappe.db.get_value(
            "Food QR", {"date": target_date, "food_type": meal_type}, "name"
        )

        if existing_name and not force_regenerate:
            frappe.db.set_value(
                "Food QR",
                existing_name,
                {
                    "day": target_day_name,
                    "food_item": food_item,
                    "food_put_count": put_count,
                },
            )
            created_or_updated.append(existing_name)
            continue

        payload = _build_qr_payload(target_date, target_day_name, meal_type, food_item, put_count)

        if existing_name:
            frappe.db.set_value("Food QR", existing_name, payload)
            created_or_updated.append(existing_name)
            continue

        qr_doc = frappe.get_doc({"doctype": "Food QR", **payload})
        if hasattr(qr_doc, "custom_dietary_preference"):
            qr_doc.custom_dietary_preference = ""
        qr_doc.insert(ignore_permissions=True)
        created_or_updated.append(qr_doc.name)

    frappe.db.commit()
    return created_or_updated


def create_food_qr_records():
    """Daily scheduler to generate Food QR records for today."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return

    try:
        created = generate_food_qr_for_date(nowdate())
        frappe.logger().info(f"[Food QR] Daily generation complete for {nowdate()} -> {created}")
    except Exception:
        frappe.logger().exception("[Food QR] Daily generation failed")


def update_food_qr_count(doc, method=None):
    """
    Keep food_put_count and per-user meal statuses in sync when Food Count changes.
    """
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return

    order_date = doc.order_date

    fresh = frappe.db.get_value(
        "Food Count",
        doc.name,
        [
            "breakfast",
            "lunch",
            "dinner",
            "breakfast_selected",
            "lunch_selected",
            "dinner_selected",
            "breakfast_status",
            "lunch_status",
            "dinner_status",
        ],
        as_dict=True,
    )

    if not fresh:
        return

    field_map = {
        "Breakfast": ("breakfast_selected", "breakfast_status"),
        "Lunch": ("lunch_selected", "lunch_status"),
        "Dinner": ("dinner_selected", "dinner_status"),
    }

    status_updates = {}

    for food_type, (selected_field, status_field) in field_map.items():
        new_count = _get_order_count(order_date, food_type)
        qr_name = frappe.db.get_value(
            "Food QR", {"date": order_date, "food_type": food_type}, "name"
        )
        if qr_name:
            frappe.db.set_value("Food QR", qr_name, "food_put_count", new_count)

        current_status = fresh.get(status_field, "") or ""
        if current_status == "Consumed":
            continue

        is_selected = int(fresh.get(selected_field, 0) or getattr(doc, selected_field, 0) or 0)
        status_updates[status_field] = "Pending" if is_selected else "Not Ordered"

    if status_updates:
        frappe.db.set_value("Food Count", doc.name, status_updates)
        frappe.db.commit()


def mark_breakfast_not_consumed():
    """Mark breakfast pending items as not consumed and close breakfast QR."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    today = nowdate()
    _mark_not_consumed(today, "breakfast_selected", "breakfast_status")
    _close_food_qr(today, "Breakfast")


def mark_lunch_not_consumed():
    """Mark lunch pending items as not consumed and close lunch QR."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    today = nowdate()
    _mark_not_consumed(today, "lunch_selected", "lunch_status")
    _close_food_qr(today, "Lunch")


def mark_dinner_not_consumed():
    """Mark dinner pending items as not consumed and close dinner QR."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    today = nowdate()
    _mark_not_consumed(today, "dinner_selected", "dinner_status")
    _close_food_qr(today, "Dinner")


def _mark_not_consumed(order_date, selected_field, status_field):
    """Convert remaining pending orders to Not Consumed for one meal slot."""
    records = frappe.get_list(
        "Food Count",
        filters=[
            ["order_date", "=", order_date],
            [selected_field, "=", 1],
            [status_field, "=", "Pending"],
        ],
        fields=["name"],
    )
    for record in records:
        frappe.db.set_value("Food Count", record["name"], status_field, "Not Consumed")
    frappe.db.commit()
    frappe.logger().info(f"[Food QR] Marked {len(records)} as Not Consumed")


def _close_food_qr(date_value, food_type):
    """Close Food QR slot after serving window ends."""
    qr_name = frappe.db.get_value("Food QR", {"date": date_value, "food_type": food_type}, "name")
    if qr_name:
        frappe.db.set_value("Food QR", qr_name, "status", "Closed")
        frappe.db.commit()


def activate_breakfast_qr():
    """Activate breakfast QR slot for today's date."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    _activate_food_qr(nowdate(), "Breakfast")


def activate_lunch_qr():
    """Activate lunch QR slot for today's date."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    _activate_food_qr(nowdate(), "Lunch")


def activate_dinner_qr():
    """Activate dinner QR slot for today's date."""
    settings = _load_settings()
    if settings and not settings.enable_meal_system:
        frappe.logger().info("[MealSystem] Disabled in settings. Skipping.")
        return
    _activate_food_qr(nowdate(), "Dinner")


def _activate_food_qr(date_value, food_type):
    """Activate Food QR slot if record exists."""
    qr_name = frappe.db.get_value("Food QR", {"date": date_value, "food_type": food_type}, "name")
    if qr_name:
        frappe.db.set_value("Food QR", qr_name, "status", "Active")
        frappe.db.commit()
        frappe.logger().info(f"[Food QR] Activated {food_type} for {date_value}")


def escalate_pending_approvals():
    """
    Send escalation reminders for pending leave and attendance approvals.
    """
    settings = _load_settings()
    if not settings:
        return

    if not settings.enable_escalation_reminders:
        return

    days = settings.escalation_days or 2
    cutoff = frappe.utils.add_days(frappe.utils.today(), -days)
    fallback_email = settings.escalation_email

    pending_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "workflow_state": ["in", ["Pending", "Pending HR Approve"]],
            "modified": ("<", cutoff),
        },
        fields=["name", "employee", "leave_approver", "from_date", "to_date", "modified"],
    )

    for leave in pending_leaves:
        recipient = leave.leave_approver or fallback_email
        if not recipient:
            continue

        frappe.sendmail(
            recipients=[recipient],
            subject=f"Action Required: Leave Application {leave.name} is awaiting your review",
            message=(
                f"This is a reminder that Leave Application {leave.name} for employee "
                f"{leave.employee} ({leave.from_date} to {leave.to_date}) has been pending "
                f"since {leave.modified} and requires your action. "
                f"Please log in to ERPNext to review."
            ),
        )

        frappe.logger().info(
            f"[Escalation] Reminder sent to {recipient} for leave {leave.name}"
        )

    pending_attendance = frappe.get_all(
        "Attendance Request",
        filters={
            "workflow_state": ["in", ["Pending", "Pending HR Approve"]],
            "modified": ("<", cutoff),
        },
        fields=["name", "employee", "approver", "workflow_state", "modified"],
    )

    for attendance in pending_attendance:
        if attendance.workflow_state == "Pending":
            recipient = attendance.approver or fallback_email
        else:
            hr_recipients = frappe.get_all(
                "Has Role",
                filters={"role": "HR Manager", "parenttype": "User"},
                pluck="parent",
            )
            recipient = hr_recipients or ([fallback_email] if fallback_email else [])
        if not recipient:
            continue

        frappe.sendmail(
            recipients=recipient if isinstance(recipient, list) else [recipient],
            subject=f"Action Required: Attendance Request {attendance.name} is awaiting your review",
            message=(
                f"Attendance Request {attendance.name} for employee {attendance.employee} "
                f"has been pending since {attendance.modified}. "
                f"Please log in to ERPNext to review."
            ),
        )

        frappe.logger().info(
            f"[Escalation] Reminder sent to {recipient} for attendance request {attendance.name}"
        )

    frappe.logger().info(
        f"[Escalation] Processed {len(pending_leaves)} leave(s) and "
        f"{len(pending_attendance)} attendance request(s)."
    )


def lock_attendance_for_processed_payroll():
    """
    Lock submitted Attendance records for periods covered by submitted payroll entries.
    """
    settings = get_settings()
    if not settings.enable_payroll_period_lock:
        return

    submitted_payrolls = frappe.get_all(
        "Payroll Entry",
        filters={"docstatus": 1},
        fields=["start_date", "end_date"],
    )

    for payroll in submitted_payrolls:
        frappe.db.sql(
            """
            UPDATE `tabAttendance`
            SET custom_locked = 1
            WHERE attendance_date BETWEEN %(start)s AND %(end)s
            AND docstatus = 1
            AND (custom_locked IS NULL OR custom_locked = 0)
            """,
            {
                "start": payroll.start_date,
                "end": payroll.end_date,
            },
        )

    frappe.db.commit()
    frappe.logger().info(
        f"[PayrollLock] Locked attendance for {len(submitted_payrolls)} payroll period(s)."
    )
