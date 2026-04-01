import frappe
from frappe.tests.utils import FrappeTestCase


class TestFoodMenuItem(FrappeTestCase):
	"""Real tests for Food Menu Item DocType."""

	def setUp(self):
		self.test_records = []

	def tearDown(self):
		for name in self.test_records:
			frappe.db.delete("Food Menu Item", {"name": name})
		frappe.db.commit()

	def test_menu_item_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "Food Menu Item",
				"day": "Monday",
				"breakfast_item": "Idli",
				"lunch_item": "Meals",
				"dinner_item": "Chapati",
				"available": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_records.append(doc.name)
		self.assertEqual(doc.day, "Monday")

	def test_menu_item_requires_breakfast_item(self):
		with self.assertRaises(Exception):
			doc = frappe.get_doc(
				{
					"doctype": "Food Menu Item",
					"day": "Monday",
					"lunch_item": "Meals",
					"dinner_item": "Chapati",
				}
			)
			doc.insert(ignore_permissions=True)
