# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate

from finstein_hrms import api
from finstein_hrms import scheduled_tasks


class TestFoodQR(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = nowdate()
        cls.day_name = getdate(cls.today).strftime("%A")
        cls.test_user = cls._ensure_user()
        cls._ensure_menu_for_day()

    @classmethod
    def _ensure_user(cls):
        email = "food-test@example.com"
        if frappe.db.exists("User", email):
            return email

        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Food",
                "last_name": "Tester",
                "username": "foodtester",
                "new_password": "Test@123",
                "roles": [{"role": "Employee"}],
            }
        ).insert(ignore_permissions=True)
        return email

    @classmethod
    def _ensure_menu_for_day(cls):
        if frappe.db.exists("Food Menu Item", {"day": cls.day_name}):
            return

        frappe.get_doc(
            {
                "doctype": "Food Menu Item",
                "day": cls.day_name,
                "available": 1,
                "breakfast_item": "Pongal",
                "lunch_item": "Rice",
                "dinner_item": "Dosa",
            }
        ).insert(ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete("Food Count", {"order_date": self.today})
        frappe.db.delete("Food QR", {"date": self.today})
        frappe.db.commit()

    def _create_food_count(self, breakfast=1, lunch=0, dinner=0):
        return frappe.get_doc(
            {
                "doctype": "Food Count",
                "user": self.test_user,
                "order_date": self.today,
                "breakfast_selected": breakfast,
                "lunch_selected": lunch,
                "dinner_selected": dinner,
            }
        ).insert(ignore_permissions=True)

    def test_generate_food_qr_for_date_sets_live_order_count(self):
        self._create_food_count(breakfast=1, lunch=1, dinner=0)

        generated = scheduled_tasks.generate_food_qr_for_date(self.today)

        self.assertEqual(len(generated), 3)
        breakfast_qr = frappe.get_doc(
            "Food QR", frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Breakfast"}, "name")
        )
        lunch_qr = frappe.get_doc(
            "Food QR", frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Lunch"}, "name")
        )
        dinner_qr = frappe.get_doc(
            "Food QR", frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Dinner"}, "name")
        )

        self.assertEqual(breakfast_qr.food_put_count, 1)
        self.assertEqual(lunch_qr.food_put_count, 1)
        self.assertEqual(dinner_qr.food_put_count, 0)
        self.assertEqual(breakfast_qr.status, "Scheduled")

    def test_food_count_update_syncs_qr_count_and_status(self):
        doc = self._create_food_count(breakfast=1, lunch=0, dinner=0)
        scheduled_tasks.generate_food_qr_for_date(self.today)

        doc.reload()
        doc.lunch_selected = 1
        doc.save(ignore_permissions=True)

        updated = frappe.get_doc("Food Count", doc.name)
        lunch_qr = frappe.get_doc(
            "Food QR", frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Lunch"}, "name")
        )

        self.assertEqual(updated.breakfast_status, "Pending")
        self.assertEqual(updated.lunch_status, "Pending")
        self.assertEqual(updated.dinner_status, "Not Ordered")
        self.assertEqual(lunch_qr.food_put_count, 1)

    def test_scan_food_qr_marks_consumed_and_increments_qr_count(self):
        self._create_food_count(breakfast=1, lunch=0, dinner=0)
        scheduled_tasks.generate_food_qr_for_date(self.today)
        qr_name = frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Breakfast"}, "name")
        frappe.db.set_value("Food QR", qr_name, "status", "Active")
        qr_doc = frappe.get_doc("Food QR", qr_name)

        frappe.set_user(self.test_user)
        with patch("finstein_hrms.api.now_datetime") as mocked_now:
            from datetime import datetime

            mocked_now.return_value = datetime.combine(getdate(self.today), api.DEFAULT_TIME_WINDOWS["Breakfast"]["start"])
            result = api.scan_food_qr(qr_doc.qr_data)

        updated = frappe.get_doc(
            "Food Count", frappe.db.get_value("Food Count", {"user": self.test_user, "order_date": self.today}, "name")
        )
        updated_qr = frappe.get_doc("Food QR", qr_name)

        self.assertTrue(result["success"])
        self.assertEqual(updated.breakfast_status, "Consumed")
        self.assertEqual(updated_qr.consumed_count, 1)

    def test_scan_food_qr_rejects_unordered_meal(self):
        self._create_food_count(breakfast=0, lunch=0, dinner=0)
        scheduled_tasks.generate_food_qr_for_date(self.today)
        qr_name = frappe.db.get_value("Food QR", {"date": self.today, "food_type": "Breakfast"}, "name")
        frappe.db.set_value("Food QR", qr_name, "status", "Active")
        qr_doc = frappe.get_doc("Food QR", qr_name)

        frappe.set_user(self.test_user)
        with patch("finstein_hrms.api.now_datetime") as mocked_now:
            from datetime import datetime

            mocked_now.return_value = datetime.combine(getdate(self.today), api.DEFAULT_TIME_WINDOWS["Breakfast"]["start"])
            with self.assertRaises(frappe.ValidationError):
                api.scan_food_qr(qr_doc.qr_data)
