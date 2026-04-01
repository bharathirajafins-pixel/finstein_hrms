from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestFoodQRScan(FrappeTestCase):
	"""Tests for meal QR scan endpoint in api.py."""

	def _make_qr_doc(self, status="Active", employee=None):
		doc = MagicMock()
		doc.name = "FQR-TEST"
		doc.status = status
		doc.employee = employee or frappe.session.user
		doc.food_type = "Lunch"
		doc.food_item = "Test Meal"
		doc.date = frappe.utils.today()
		doc.consumed_count = 0
		doc.food_put_count = 1
		return doc

	@patch("frappe.get_doc")
	def test_already_consumed_blocked(self, mock_get_doc):
		mock_get_doc.return_value = self._make_qr_doc(status="Consumed")
		from finstein_hrms.api import scan_food_qr

		with self.assertRaises(frappe.exceptions.ValidationError):
			scan_food_qr("TEST-QR-CONSUMED")

	@patch("frappe.get_doc")
	def test_inactive_qr_blocked(self, mock_get_doc):
		mock_get_doc.return_value = self._make_qr_doc(status="Pending")
		from finstein_hrms.api import scan_food_qr

		with self.assertRaises(frappe.exceptions.ValidationError):
			scan_food_qr("TEST-QR-INACTIVE")

	@patch("frappe.get_doc")
	def test_cancelled_qr_blocked(self, mock_get_doc):
		mock_get_doc.return_value = self._make_qr_doc(status="Cancelled")
		from finstein_hrms.api import scan_food_qr

		with self.assertRaises(frappe.exceptions.ValidationError):
			scan_food_qr("TEST-QR-CANCELLED")

	@patch("frappe.get_doc")
	def test_wrong_employee_blocked(self, mock_get_doc):
		mock_get_doc.return_value = self._make_qr_doc(status="Active", employee="other.employee@company.com")
		from finstein_hrms.api import scan_food_qr

		with self.assertRaises(frappe.exceptions.ValidationError):
			scan_food_qr("TEST-QR-WRONG-EMP")
