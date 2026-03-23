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

    def setUp(self):
        super().setUp()
        self._delete_food_counts_for_test_user()

    def tearDown(self):
        self._delete_food_counts_for_test_user()
        super().tearDown()

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

    def _delete_food_counts_for_test_user(self):
        records = frappe.get_all(
            "Food Count",
            filters={"user": frappe.session.user, "order_date": self.order_date},
            pluck="name",
        )
        for name in records:
            frappe.delete_doc("Food Count", name, force=1)

    def test_get_menu_for_date_returns_expected_items(self):
        menu = get_menu_for_date(self.order_date)
        expected = frappe.db.get_value(
            "Food Menu Item",
            self.menu_name,
            ["breakfast_item", "lunch_item", "dinner_item"],
            as_dict=True,
        )

        self.assertEqual(menu["day"], self.day_name)
        self.assertEqual(menu["breakfast_item"], expected.breakfast_item)
        self.assertEqual(menu["lunch_item"], expected.lunch_item)
        self.assertEqual(menu["dinner_item"], expected.dinner_item)

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
        expected = frappe.db.get_value(
            "Food Menu Item",
            self.menu_name,
            ["breakfast_item", "lunch_item", "dinner_item"],
            as_dict=True,
        )

        self.assertEqual(doc.user, current_user)
        self.assertEqual(str(doc.order_date), self.order_date)
        self.assertEqual(doc.breakfast, expected.breakfast_item)
        self.assertEqual(doc.lunch, expected.lunch_item)
        self.assertEqual(doc.dinner, expected.dinner_item)
