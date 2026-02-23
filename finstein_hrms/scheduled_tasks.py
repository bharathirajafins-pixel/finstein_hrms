import frappe
import uuid
from frappe.utils import add_days, nowdate, getdate
from datetime import time

# ============================================================
# File: apps/your_app/your_app/scheduled_tasks.py
# ============================================================

# ── Time Windows ─────────────────────────────────────────────
TIME_WINDOWS = {
    "Breakfast": {"start": time(9,  0),  "end": time(11, 0),  "serving": "08:00:00"},
    "Lunch":     {"start": time(12, 30), "end": time(15, 0),  "serving": "12:30:00"},
    "Dinner":    {"start": time(19, 0),  "end": time(22, 0),  "serving": "19:00:00"},
}


def _get_order_count(order_date, food_type):
    field_map = {"Breakfast": "breakfast", "Lunch": "lunch", "Dinner": "dinner"}
    db_field  = field_map.get(food_type)
    if not db_field:
        return 0
    return frappe.db.count("Food Count", filters=[
        ["order_date", "=", order_date],
        [db_field,    "!=", ""]
    ])


# ============================================================
# SCHEDULED: 12:01 AM — Create Food QR records for tomorrow
# ============================================================
def create_food_qr_records():
    tomorrow      = add_days(nowdate(), 1)
    tomorrow_date = getdate(tomorrow)
    day_names     = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    day_name      = day_names[tomorrow_date.weekday()]

    menu_list = frappe.get_list(
        "Food Menu Item",
        filters=[["day", "=", day_name], ["available", "=", 1]],
        fields=["name", "breakfast_item", "lunch_item", "dinner_item"],
        limit=1
    )
    if not menu_list:
        frappe.logger().warning(f"[Food QR] No menu for {day_name}")
        return

    menu       = menu_list[0]
    meal_items = {
        "Breakfast": menu.get("breakfast_item"),
        "Lunch":     menu.get("lunch_item"),
        "Dinner":    menu.get("dinner_item")
    }

    for food_type, food_item in meal_items.items():
        if not food_item:
            continue
        if frappe.db.exists("Food QR", {"date": tomorrow, "food_type": food_type}):
            continue

        win       = TIME_WINDOWS[food_type]
        put_count = _get_order_count(tomorrow, food_type)
        unique_id = uuid.uuid4().hex[:10].upper()
        qr_data   = f"FQR|{tomorrow}|{food_type}|{unique_id}"
        qr_url    = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_data}"

        qr_doc = frappe.get_doc({
            "doctype":        "Food QR",
            "date":           tomorrow,
            "day":            day_name,
            "food_type":      food_type,
            "food_item":      food_item,
            "serving_time":   win["serving"],
            "window_start":   win["start"].strftime("%H:%M:%S"),
            "window_end":     win["end"].strftime("%H:%M:%S"),
            "status":         "Scheduled",
            "food_put_count": put_count,
            "consumed_count": 0,
            "qr_data":        qr_data,
            "qr_image_url":   qr_url,
            "qr_display": (
                f'<div style="text-align:center;padding:20px;">'
                f'<img src="{qr_url}" style="width:240px;height:240px;'
                f'border-radius:12px;border:3px solid #f39c12;">'
                f'<p style="margin-top:10px;font-weight:700;font-size:16px;">'
                f'{food_type} — {food_item}</p>'
                f'<p style="color:#888;font-size:12px;">{day_name}, {tomorrow}</p>'
                f'<p style="color:#aaa;font-size:11px;">Window: '
                f'{win["start"].strftime("%I:%M %p")} – {win["end"].strftime("%I:%M %p")}</p>'
                f'</div>'
            )
        })
        qr_doc.insert(ignore_permissions=True)
        frappe.logger().info(f"[Food QR] Created {food_type} | put_count={put_count}")

    frappe.db.commit()
    print(f"✅ Food QR records created for {day_name} {tomorrow}")


# ============================================================
# DOC EVENT: Food Count after_insert / on_update
# ============================================================
def update_food_qr_count(doc, method=None):
    """
    1. Updates food_put_count in Food QR live
    2. Sets meal status on Food Count:
       ordered   → Pending
       cleared   → Not Ordered
       Consumed  → unchanged (never overwritten)
    """
    order_date = doc.order_date

    # Always reload from DB to get latest saved values
    # (doc object in on_update may have stale data)
    fresh = frappe.db.get_value(
        "Food Count",
        doc.name,
        ["breakfast", "lunch", "dinner",
         "breakfast_status", "lunch_status", "dinner_status"],
        as_dict=True
    )

    if not fresh:
        return

    field_map = {
        "Breakfast": ("breakfast", "breakfast_status"),
        "Lunch":     ("lunch",     "lunch_status"),
        "Dinner":    ("dinner",    "dinner_status"),
    }

    status_updates = {}

    for food_type, (item_field, status_field) in field_map.items():

        # ── Update food_put_count in Food QR ─────────────────
        new_count = _get_order_count(order_date, food_type)
        qr_name   = frappe.db.get_value("Food QR",
            {"date": order_date, "food_type": food_type}, "name")
        if qr_name:
            frappe.db.set_value("Food QR", qr_name, "food_put_count", new_count)

        # ── Update status on Food Count ───────────────────────
        # Never overwrite a Consumed status
        current_status = fresh.get(status_field, "") or ""
        if current_status == "Consumed":
            continue

        # Use fresh DB value first, fall back to doc attribute
        item_value = fresh.get(item_field, "") or getattr(doc, item_field, "") or ""
        status_updates[status_field] = "Pending" if item_value.strip() else "Not Ordered"

    if status_updates:
        frappe.db.set_value("Food Count", doc.name, status_updates)
        # Force immediate DB flush so UI refresh shows updated status
        frappe.db.commit()


# ============================================================
# SCHEDULED: Mark Not Consumed + Close QR after window ends
# ============================================================
def mark_breakfast_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "breakfast", "breakfast_status")
    _close_food_qr(today, "Breakfast")

def mark_lunch_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "lunch", "lunch_status")
    _close_food_qr(today, "Lunch")

def mark_dinner_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "dinner", "dinner_status")
    _close_food_qr(today, "Dinner")

def _mark_not_consumed(order_date, item_field, status_field):
    records = frappe.get_list(
        "Food Count",
        filters=[
            ["order_date", "=",  order_date],
            [item_field,   "!=", ""],
            [status_field, "=",  "Pending"]
        ],
        fields=["name"]
    )
    for r in records:
        frappe.db.set_value("Food Count", r["name"], status_field, "Not Consumed")
    frappe.db.commit()
    frappe.logger().info(f"[Food QR] Marked {len(records)} as Not Consumed")

def _close_food_qr(date, food_type):
    qr_name = frappe.db.get_value("Food QR",
        {"date": date, "food_type": food_type}, "name")
    if qr_name:
        frappe.db.set_value("Food QR", qr_name, "status", "Closed")
        frappe.db.commit()


# ============================================================
# SCHEDULED: Activate QR at window start
# ============================================================
def activate_breakfast_qr():
    _activate_food_qr(nowdate(), "Breakfast")

def activate_lunch_qr():
    _activate_food_qr(nowdate(), "Lunch")

def activate_dinner_qr():
    _activate_food_qr(nowdate(), "Dinner")

def _activate_food_qr(date, food_type):
    qr_name = frappe.db.get_value("Food QR",
        {"date": date, "food_type": food_type}, "name")
    if qr_name:
        frappe.db.set_value("Food QR", qr_name, "status", "Active")
        frappe.db.commit()
        frappe.logger().info(f"[Food QR] Activated {food_type} for {date}")