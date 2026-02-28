import frappe
import uuid
from frappe.utils import nowdate, getdate
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

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _get_order_count(order_date, food_type):
    field_map = {
        "Breakfast": "breakfast_selected",
        "Lunch": "lunch_selected",
        "Dinner": "dinner_selected",
    }
    db_field  = field_map.get(food_type)
    if not db_field:
        return 0
    return frappe.db.count("Food Count", filters=[
        ["order_date", "=", order_date],
        [db_field, "=", 1]
    ])


def _build_qr_payload(target_date, day_name, food_type, food_item, put_count):
    win = TIME_WINDOWS[food_type]
    unique_id = uuid.uuid4().hex[:10].upper()
    qr_data = f"FQR|{target_date}|{food_type}|{unique_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_data}"

    return {
        "date": target_date,
        "day": day_name,
        "food_type": food_type,
        "food_item": food_item,
        "serving_time": win["serving"],
        "window_start": win["start"].strftime("%H:%M:%S"),
        "window_end": win["end"].strftime("%H:%M:%S"),
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
            f'{food_type} — {food_item}</p>'
            f'<p style="color:#888;font-size:12px;">{day_name}, {target_date}</p>'
            f'<p style="color:#aaa;font-size:11px;">Window: '
            f'{win["start"].strftime("%I:%M %p")} – {win["end"].strftime("%I:%M %p")}</p>'
            f'</div>'
        ),
    }


def generate_food_qr_for_date(target_date, food_type=None, force_regenerate=False):
    """
    Generate Food QR for a specific date.
    - If food_type is provided, generates/updates only that slot.
    - If food_type is None, generates/updates all meal slots available in menu.
    """
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

        # Keep existing QR unless regenerate is explicitly requested.
        if existing_name and not force_regenerate:
            frappe.db.set_value("Food QR", existing_name, {
                "day": target_day_name,
                "food_item": food_item,
                "food_put_count": put_count,
            })
            created_or_updated.append(existing_name)
            continue

        payload = _build_qr_payload(target_date, target_day_name, meal_type, food_item, put_count)

        if existing_name:
            frappe.db.set_value("Food QR", existing_name, payload)
            created_or_updated.append(existing_name)
            continue

        qr_doc = frappe.get_doc({"doctype": "Food QR", **payload})
        qr_doc.insert(ignore_permissions=True)
        created_or_updated.append(qr_doc.name)

    frappe.db.commit()
    return created_or_updated


# ============================================================
# SCHEDULED: Daily — Create Food QR records for today
# ============================================================
def create_food_qr_records():
    try:
        created = generate_food_qr_for_date(nowdate())
        frappe.logger().info(f"[Food QR] Daily generation complete for {nowdate()} -> {created}")
    except Exception:
        frappe.logger().exception("[Food QR] Daily generation failed")


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
         "breakfast_selected", "lunch_selected", "dinner_selected",
         "breakfast_status", "lunch_status", "dinner_status"],
        as_dict=True
    )

    if not fresh:
        return

    field_map = {
        "Breakfast": ("breakfast_selected", "breakfast_status"),
        "Lunch":     ("lunch_selected",     "lunch_status"),
        "Dinner":    ("dinner_selected",    "dinner_status"),
    }

    status_updates = {}

    for food_type, (selected_field, status_field) in field_map.items():

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

        # Use selected checkbox to decide if ordered.
        is_selected = int(fresh.get(selected_field, 0) or getattr(doc, selected_field, 0) or 0)
        status_updates[status_field] = "Pending" if is_selected else "Not Ordered"

    if status_updates:
        frappe.db.set_value("Food Count", doc.name, status_updates)
        # Force immediate DB flush so UI refresh shows updated status
        frappe.db.commit()


# ============================================================
# SCHEDULED: Mark Not Consumed + Close QR after window ends
# ============================================================
def mark_breakfast_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "breakfast_selected", "breakfast_status")
    _close_food_qr(today, "Breakfast")

def mark_lunch_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "lunch_selected", "lunch_status")
    _close_food_qr(today, "Lunch")

def mark_dinner_not_consumed():
    today = nowdate()
    _mark_not_consumed(today, "dinner_selected", "dinner_status")
    _close_food_qr(today, "Dinner")

def _mark_not_consumed(order_date, selected_field, status_field):
    records = frappe.get_list(
        "Food Count",
        filters=[
            ["order_date", "=", order_date],
            [selected_field, "=", 1],
            [status_field, "=", "Pending"]
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
