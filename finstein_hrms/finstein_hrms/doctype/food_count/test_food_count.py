# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate, getdate

from finstein_hrms.finstein_hrms.doctype.food_count.food_count import get_menu_for_date


class TestFoodCount(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order_date = add_days(nowdate(), 1)
        cls.day_name = getdate(cls.order_date).strftime("%A")
        cls._ensure_menu_for_day()

    @classmethod
    def _ensure_menu_for_day(cls):
        existing = frappe.db.get_value("Food Menu Item", {"day": cls.day_name}, "name")
        if existing:
            cls.menu_name = existing
            return

        cls.menu_name = frappe.get_doc(
            {
                "doctype": "Food Menu Item",
                "day": cls.day_name,
                "available": 1,
                "breakfast_item": "Idli",
                "lunch_item": "Meals",
                "dinner_item": "Chapati",
            }
        ).insert(ignore_permissions=True).name

    def test_get_menu_for_date_returns_expected_items(self):
        menu = get_menu_for_date(self.order_date)

        self.assertEqual(menu["day"], self.day_name)
        self.assertEqual(menu["breakfast_item"], "Idli")
        self.assertEqual(menu["lunch_item"], "Meals")
        self.assertEqual(menu["dinner_item"], "Chapati")

    def test_validate_sets_default_user_date_and_meal_items(self):
        doc = frappe.get_doc(
            {
                "doctype": "Food Count",
                "breakfast_selected": 1,
                "lunch_selected": 0,
                "dinner_selected": 1,
            }
        )

        current_user = frappe.session.user
        doc.insert(ignore_permissions=True)

        self.assertEqual(doc.user, current_user)
        self.assertEqual(str(doc.order_date), self.order_date)
        self.assertEqual(doc.breakfast, "Idli")
        self.assertEqual(doc.lunch, "Meals")
        self.assertEqual(doc.dinner, "Chapati")
