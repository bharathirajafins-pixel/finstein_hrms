from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAttendanceRequestValidation(FrappeTestCase):
	"""Tests for attendance_request_validation.py business rules."""

	def _make_settings(self, **kwargs):
		s = MagicMock()
		s.max_attendance_requests_per_month = kwargs.get("max_req", 5)
		s.restrict_to_current_month = kwargs.get("curr_month", 1)
		s.allowed_attendance_statuses = kwargs.get("statuses", "Present\nWork From Home\nHalf Day")
		return s

	def _make_doc(self, **kwargs):
		doc = MagicMock()
		doc.employee = kwargs.get("employee", "_Test Employee")
		doc.name = kwargs.get("name", "ATT-REQ-TEST")
		doc.from_date = kwargs.get("from_date", frappe.utils.add_days(frappe.utils.today(), -1))
		doc.to_date = kwargs.get("to_date", frappe.utils.add_days(frappe.utils.today(), -1))
		doc.attendance_type = kwargs.get("attendance_type", "Present")
		doc.workflow_state = kwargs.get("workflow_state", "Draft")
		doc.approver = kwargs.get("approver")
		return doc

	@patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
	@patch("finstein_hrms.server_script.attendance_request_validation.check_attendance_not_locked")
	@patch("frappe.db.get_value", return_value=None)
	def test_future_date_blocked(self, mock_get_value, mock_not_locked, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.attendance_request_validation import (
			validate_attendance_request,
		)

		doc = self._make_doc(
			from_date=frappe.utils.add_days(frappe.utils.today(), 2),
			to_date=frappe.utils.add_days(frappe.utils.today(), 2),
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_attendance_request(doc, None)

	@patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
	@patch("finstein_hrms.server_script.attendance_request_validation.check_attendance_not_locked")
	@patch("frappe.db.get_value", return_value=None)
	def test_valid_past_date_passes(self, mock_get_value, mock_not_locked, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.attendance_request_validation import (
			validate_attendance_request,
		)

		doc = self._make_doc()
		try:
			validate_attendance_request(doc, None)
		except frappe.exceptions.ValidationError:
			self.fail("Valid past date raised error unexpectedly.")

	@patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
	@patch("frappe.db.count", return_value=5)
	@patch("finstein_hrms.server_script.attendance_request_validation.check_attendance_not_locked")
	@patch("frappe.db.get_value", return_value=None)
	def test_max_requests_per_month_blocked(self, mock_get_value, mock_not_locked, mock_count, mock_settings):
		mock_settings.return_value = self._make_settings(max_req=5)
		from finstein_hrms.server_script.attendance_request_validation import (
			validate_attendance_request,
		)

		doc = self._make_doc()
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_attendance_request(doc, None)

	@patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
	@patch("finstein_hrms.server_script.attendance_request_validation.check_attendance_not_locked")
	@patch("frappe.db.get_value", return_value=None)
	def test_invalid_status_blocked(self, mock_get_value, mock_not_locked, mock_settings):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.attendance_request_validation import (
			validate_attendance_request,
		)

		doc = self._make_doc(attendance_type="On Leave")
		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_attendance_request(doc, None)

	@patch("frappe.db.get_value")
	def test_maps_shift_request_approver_for_employee(self, mock_get_value):
		from finstein_hrms.server_script.attendance_request_validation import (
			_set_attendance_request_approver,
		)

		def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
			if doctype == "Employee" and fieldname == "user_id":
				return "demo.employee@finstein.local"
			if doctype == "Employee" and fieldname == "shift_request_approver":
				return "demo.tl@finstein.local"
			if doctype == "Has Role":
				return None
			return None

		mock_get_value.side_effect = fake_get_value
		doc = self._make_doc(workflow_state="Pending", approver=None)

		_set_attendance_request_approver(doc)

		self.assertEqual(doc.approver, "demo.tl@finstein.local")

	@patch("frappe.db.get_value")
	def test_team_leader_can_skip_tl_without_assigned_approver(self, mock_get_value):
		from finstein_hrms.server_script.attendance_request_validation import (
			_set_attendance_request_approver,
		)

		def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
			if doctype == "Employee" and fieldname == "user_id":
				return "demo.tl@finstein.local"
			if doctype == "Employee" and fieldname == "shift_request_approver":
				return None
			if doctype == "Has Role":
				return "HAS-ROLE-ROW"
			return None

		mock_get_value.side_effect = fake_get_value
		doc = self._make_doc(workflow_state="Pending HR Approve", approver=None)

		_set_attendance_request_approver(doc)

		self.assertIsNone(doc.approver)
