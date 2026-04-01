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
		doc.employee_name = "Test Employee"
		doc.log_type = log_type
		doc.time = frappe.utils.now()
		doc.attendance_date = frappe.utils.today()
		doc.checkout_time = None
		doc.checkout_type = "Normal"
		doc.timesheet = None
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

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.get_doc")
	@patch("frappe.db.exists", return_value=False)
	@patch("frappe.get_roles", return_value=["Employee"])
	def test_checkout_blocked_when_timesheet_is_incomplete_draft(
		self, mock_roles, mock_exists, mock_get_doc, mock_settings
	):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="IN")
		doc.checkout_time = frappe.utils.add_to_date(doc.time, hours=8)
		doc.timesheet = "TS-0001"
		mock_get_doc.return_value = MagicMock(
			docstatus=0,
			get=MagicMock(
				return_value=[MagicMock(activity_type="", from_time=doc.time, to_time=doc.time, hours=0)]
			),
		)

		with self.assertRaises(frappe.exceptions.ValidationError):
			validate_checkin(doc, None)

	@patch("finstein_hrms.server_script.checkin_validation.get_settings")
	@patch("frappe.get_doc")
	@patch("frappe.db.exists", return_value=False)
	@patch("frappe.get_roles", return_value=["Employee"])
	def test_checkout_allowed_when_timesheet_is_saved_with_activity_type(
		self, mock_roles, mock_exists, mock_get_doc, mock_settings
	):
		mock_settings.return_value = self._make_settings()
		from finstein_hrms.server_script.checkin_validation import validate_checkin

		doc = self._make_doc(log_type="IN")
		doc.checkout_time = frappe.utils.add_to_date(doc.time, hours=8)
		doc.timesheet = "TS-0001"
		mock_get_doc.return_value = MagicMock(
			docstatus=0,
			get=MagicMock(
				return_value=[
					MagicMock(activity_type="Execution", from_time=doc.time, to_time=doc.time, hours=0)
				]
			),
		)

		try:
			validate_checkin(doc, None)
		except frappe.exceptions.ValidationError:
			self.fail("Saved draft timesheet with activity type should allow checkout.")

	@patch("frappe.db.set_value")
	@patch("frappe.new_doc")
	@patch("frappe.get_doc")
	def test_ensure_timesheet_for_checkin_creates_and_links_draft(
		self, mock_get_doc, mock_new_doc, mock_set_value
	):
		from finstein_hrms.server_script.checkin_validation import ensure_timesheet_for_checkin

		checkin = self._make_doc(log_type="IN")
		mock_get_doc.return_value = checkin

		ts = MagicMock()
		ts.name = "TS-0001"
		ts.docstatus = 0
		mock_new_doc.return_value = ts

		result = ensure_timesheet_for_checkin(checkin.name)

		self.assertEqual(result["timesheet"], "TS-0001")
		self.assertEqual(result["docstatus"], 0)
		ts.append.assert_called_once_with(
			"time_logs",
			{
				"from_time": checkin.time,
				"to_time": checkin.time,
				"hours": 0,
			},
		)
		mock_set_value.assert_called_once_with(
			"Employee Checkin", checkin.name, "timesheet", "TS-0001", update_modified=False
		)

	def test_timesheet_required_message_matches_ui_copy(self):
		from finstein_hrms.server_script.checkin_validation import _timesheet_required_message

		self.assertEqual(
			_timesheet_required_message(),
			"Please complete and save your timesheet before checking out.",
		)
