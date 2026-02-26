import frappe
from frappe.utils import nowdate, now_datetime
from datetime import time

# ============================================================
# File: apps/your_app/your_app/api.py
# ============================================================

TIME_WINDOWS = {
    "Breakfast": {"start": time(9,  0),  "end": time(11, 0)},
    "Lunch":     {"start": time(12, 30), "end": time(15, 0)},
    "Dinner":    {"start": time(19, 0),  "end": time(22, 0)},
}

def _window_str(food_type):
    win = TIME_WINDOWS.get(food_type)
    if not win:
        return ""
    return f"{win['start'].strftime('%I:%M %p')} - {win['end'].strftime('%I:%M %p')}"


@frappe.whitelist(allow_guest=False)
def scan_food_qr(qr_data):
    """
    Called from employee phone when they scan the provider's meal QR.

    Validations (in order):
      1. QR format valid
      2. Food QR record exists
      3. Food QR status is Active (not Scheduled/Closed)
      4. Current time is within meal window
      5. Employee has a Food Count for today
      6. Employee ordered this meal type
      7. Not already Consumed (block duplicate scan)

    On success:
      - Food Count meal status -> Consumed
      - Food QR consumed_count +1
    """
    employee = frappe.session.user
    today    = nowdate()
    now_time = now_datetime().time()

    # 1. Format check
    if not qr_data:
        frappe.throw("QR data is missing.")
    parts = str(qr_data).strip().split("|")
    if len(parts) != 4 or parts[0] != "FQR":
        frappe.throw("Invalid QR code. Please scan the correct meal QR.")

    qr_food_type = parts[2]  # Breakfast / Lunch / Dinner

    # 2. Find Food QR record
    qr_name = frappe.db.get_value("Food QR", {"qr_data": qr_data}, "name")
    if not qr_name:
        frappe.throw("QR code not recognised. Please try again.")

    qr_doc = frappe.get_doc("Food QR", qr_name)

    # 3. Status check
    if qr_doc.status == "Scheduled":
        win = TIME_WINDOWS.get(qr_food_type, {})
        open_time = win["start"].strftime("%I:%M %p") if win.get("start") else ""
        frappe.throw(f"{qr_doc.food_type} QR is not active yet. Opens at {open_time}.")

    if qr_doc.status == "Closed":
        frappe.throw(
            f"{qr_doc.food_type} session is closed. "
            f"Window was {_window_str(qr_food_type)}."
        )

    # 4. Time window check
    win = TIME_WINDOWS.get(qr_food_type)
    if not win:
        frappe.throw(f"Unknown food type: {qr_food_type}")

    if not (win["start"] <= now_time <= win["end"]):
        frappe.throw(
            f"Outside serving window. "
            f"{qr_food_type} is only available {_window_str(qr_food_type)}."
        )

    # 5. Find employee Food Count for today
    food_count_name = frappe.db.get_value("Food Count", {
        "user":       employee,
        "order_date": today
    }, "name")

    if not food_count_name:
        frappe.throw(
            "No order found for you today. "
            "You must place your order the day before to collect food."
        )

    food_count = frappe.get_doc("Food Count", food_count_name)

    # 6. Check meal was ordered
    field_map = {
        "Breakfast": ("breakfast", "breakfast_status"),
        "Lunch":     ("lunch",     "lunch_status"),
        "Dinner":    ("dinner",    "dinner_status"),
    }
    item_field, status_field = field_map[qr_food_type]
    ordered_item   = getattr(food_count, item_field,   "")
    current_status = getattr(food_count, status_field, "")

    if not ordered_item:
        frappe.throw(
            f"You did not order {qr_food_type} for today. "
            f"Only ordered meals can be collected."
        )

    # 7. Block duplicate scan
    if current_status == "Consumed":
        frappe.throw(
            f"Already consumed! You already collected your {qr_food_type} today."
        )

    # 8. Mark Consumed + increment
    frappe.db.set_value("Food Count", food_count_name, status_field, "Consumed")
    new_count = (qr_doc.consumed_count or 0) + 1
    frappe.db.set_value("Food QR", qr_name, "consumed_count", new_count)
    frappe.db.commit()

    return {
        "success":        True,
        "food_type":      qr_doc.food_type,
        "food_item":      qr_doc.food_item,
        "consumed_count": new_count,
        "put_count":      qr_doc.food_put_count,
        "message": (
            f"Enjoy your {qr_doc.food_type}! "
            f"{qr_doc.food_item} collected. "
            f"({new_count}/{qr_doc.food_put_count} served today)"
        )
    }



@frappe.whitelist(allow_guest=False)
def get_todays_food_qr():
    """Provider webpage: returns today's 3 Food QR slots with live counts."""
    return frappe.get_list(
        "Food QR",
        filters=[["date", "=", nowdate()]],
        fields=[
            "name", "date", "day", "food_type", "food_item",
            "serving_time", "window_start", "window_end",
            "status", "food_put_count", "consumed_count",
            "qr_data", "qr_image_url", "vendor"
        ],
        order_by="serving_time asc"
    )


@frappe.whitelist(allow_guest=False)
def get_my_order_status():
    """Employee app: returns today's meal statuses for logged-in user."""
    name = frappe.db.get_value("Food Count", {
        "user":       frappe.session.user,
        "order_date": nowdate()
    }, "name")

    if not name:
        return None

    doc = frappe.get_doc("Food Count", name)
    return {
        "breakfast":        doc.breakfast,
        "breakfast_status": doc.breakfast_status,
        "lunch":            doc.lunch,
        "lunch_status":     doc.lunch_status,
        "dinner":           doc.dinner,
        "dinner_status":    doc.dinner_status,
    }
