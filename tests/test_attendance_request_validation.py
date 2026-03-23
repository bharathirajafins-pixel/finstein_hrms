import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock


class TestAttendanceRequestValidation(FrappeTestCase):
    """Tests for attendance_request_validation.py business rules."""

    def _make_settings(self, **kwargs):
        s = MagicMock()
        s.max_attendance_requests_per_month = kwargs.get("max_req", 5)
        s.restrict_to_current_month = kwargs.get("curr_month", 1)
        s.allowed_attendance_statuses = kwargs.get(
            "statuses", "Present\nWork From Home\nHalf Day"
        )
        return s

    def _make_doc(self, **kwargs):
        doc = MagicMock()
        doc.employee = kwargs.get("employee", "_Test Employee")
        doc.name = kwargs.get("name", "ATT-REQ-TEST")
        doc.from_date = kwargs.get("from_date", frappe.utils.add_days(frappe.utils.today(), -1))
        doc.to_date = kwargs.get("to_date", frappe.utils.add_days(frappe.utils.today(), -1))
        doc.attendance_type = kwargs.get("attendance_type", "Present")
        return doc

    @patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
    def test_future_date_blocked(self, mock_settings):
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
    def test_valid_past_date_passes(self, mock_settings):
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
    def test_max_requests_per_month_blocked(self, mock_count, mock_settings):
        mock_settings.return_value = self._make_settings(max_req=5)
        from finstein_hrms.server_script.attendance_request_validation import (
            validate_attendance_request,
        )

        doc = self._make_doc()
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_attendance_request(doc, None)

    @patch("finstein_hrms.server_script.attendance_request_validation.get_settings")
    def test_invalid_status_blocked(self, mock_settings):
        mock_settings.return_value = self._make_settings()
        from finstein_hrms.server_script.attendance_request_validation import (
            validate_attendance_request,
        )

        doc = self._make_doc(attendance_type="On Leave")
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_attendance_request(doc, None)
