# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, getdate, cint, add_days
from frappe.model.document import Document

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@frappe.whitelist()
def get_menu_for_date(order_date=None):
    """Return the available food menu items for the given date."""
    order_date = order_date or add_days(nowdate(), 1)
    day_name = DAY_NAMES[getdate(order_date).weekday()]

    menu = frappe.db.get_value(
        "Food Menu Item",
        {"day": day_name, "available": 1},
        ["breakfast_item", "lunch_item", "dinner_item"],
        as_dict=True,
    ) or {}

    return {
        "day": day_name,
        "breakfast_item": menu.get("breakfast_item") or "",
        "lunch_item": menu.get("lunch_item") or "",
        "dinner_item": menu.get("dinner_item") or "",
    }


class FoodCount(Document):
    def before_insert(self):
        self._set_defaults()

    def validate(self):
        self._set_defaults()
        self._apply_menu_selection()

    def _set_defaults(self):
        if not self.user:
            self.user = frappe.session.user
        if not self.order_date:
            self.order_date = add_days(nowdate(), 1)

    def _apply_menu_selection(self):
        menu = get_menu_for_date(self.order_date)

        slot_map = (
            ("breakfast_selected", "breakfast", "breakfast_item", "Breakfast"),
            ("lunch_selected", "lunch", "lunch_item", "Lunch"),
            ("dinner_selected", "dinner", "dinner_item", "Dinner"),
        )

        for check_field, item_field, menu_field, slot_label in slot_map:
            selected = cint(getattr(self, check_field, 0))
            menu_item = menu.get(menu_field) or ""

            if selected and not menu_item:
                frappe.throw(f"{slot_label} menu is not available for {menu.get('day')}.")

            # Always show menu item in field; checkbox controls counting/ordering.
            setattr(self, item_field, menu_item)
