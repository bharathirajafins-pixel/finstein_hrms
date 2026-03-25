from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCheckinValidation(FrappeTestCase):
	"""Tests for checkin_validation.py business rules."""

	def _make_settings(self, **kwargs):
		s = MagicMock()
		s.min_checkin_hours = kwargs.get("min_hours", 8.0)
		s.enable_late_entry_tagging = kwargs.get("late_tag", 1)
		s.enable_overtime_tracking = kwargs.get("overtime", 1)
		s.shift_start_time = kwargs.get("shift_start", "09:00:00")
		s.shift_end_time = kwargs.get("shift_end", "18:00:00")
		s.enable_force_checkout = kwargs.get("force_checkout", 1)
		return s

	def _make_doc(self, log_type="IN"):
		doc = MagicMock()
		doc.name = "CHK-TEST"
		doc.employee = "_Test Employee"
		doc.log_type = log_type
		doc.time = frappe.utils.now()
		doc.attendance_date = frappe.utils.today()
		doc.checkout_time = None
		doc.checkout_type = "Normal"
		doc.break_hours = 0
		doc.working_hours = None
		return doc

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.db.exists", return_value=True)
	@patch("frappe.get_roles", return_value=["Employee"])
	def test_duplicate_checkin_blocked(self, mock_roles, mock_exists, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="IN")
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_checkin(doc, None)

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.db.exists", return_value=False)
	@patch("frappe.get_roles", return_value=["Employee"])
	def test_valid_checkin_passes(self, mock_roles, mock_exists, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="IN")
		try:
			validate_checkin(doc, None)
		except frappe.exceptions.ValidationError:
			self.fail("Valid checkin raised error unexpectedly.")

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.db.exists", return_value=False)
	@patch("frappe.db.get_value", return_value=None)
	@patch("frappe.get_roles", return_value=["Employee"])
	def test_checkout_without_checkin_blocked(self, mock_roles, mock_get, mock_exists, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="OUT")
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_checkin(doc, None)

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.get_roles", return_value=["System Manager"])
	def test_admin_checkin_blocked(self, mock_roles, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="IN")
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_checkin(doc, None)
