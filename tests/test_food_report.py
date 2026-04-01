import frappe
from frappe.tests.utils import FrappeTestCase


class TestFoodReport(FrappeTestCase):
	"""Tests for Food Report DocType."""

	def setUp(self):
		self.test_records = []

	def tearDown(self):
		for name in self.test_records:
			frappe.db.delete("Food Report", {"name": name})
		frappe.db.commit()

	def test_food_report_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "Food Report",
				"user": frappe.session.user,
				"report_date": frappe.utils.today(),
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_records.append(doc.name)
		self.assertEqual(str(doc.report_date), frappe.utils.today())

	def test_food_report_requires_date(self):
		with self.assertRaises(Exception):
			doc = frappe.get_doc({"doctype": "Food Report", "user": frappe.session.user})
			doc.insert(ignore_permissions=True)
