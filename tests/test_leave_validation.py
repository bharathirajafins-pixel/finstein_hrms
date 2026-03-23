import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock


class TestLeaveValidation(FrappeTestCase):
    """Tests for leave_validation.py business rules."""

    def _make_settings(self, **kwargs):
        s = MagicMock()
        s.max_continuous_leave_days = kwargs.get("max_days", 3)
        s.leave_submission_cutoff_time = kwargs.get("cutoff", "17:00:00")
        s.half_day_cutoff_time = kwargs.get("half_cut", "12:00:00")
        s.allow_past_date_leave = kwargs.get("allow_past", 0)
        s.enable_leave_balance_check = kwargs.get("balance_check", 1)
        s.enable_leave_withdrawal = kwargs.get("withdrawal", 1)
        return s

    def _make_doc(self, **kwargs):
        doc = MagicMock()
        doc.from_date = kwargs.get("from_date", frappe.utils.add_days(frappe.utils.today(), 2))
        doc.to_date = kwargs.get("to_date", frappe.utils.add_days(frappe.utils.today(), 2))
        doc.custom_from_time = kwargs.get("from_time", "09:00:00")
        doc.custom_to_time = kwargs.get("to_time", "17:00:00")
        doc.half_day = kwargs.get("half_day", 0)
        doc.half_day_date = kwargs.get("half_day_date", doc.from_date)
        doc.employee = kwargs.get("employee", "_Test Employee")
        doc.leave_type = kwargs.get("leave_type", "Casual Leave")
        doc.docstatus = kwargs.get("docstatus", 0)
        return doc

    @patch("finstein_hrms.server_script.leave_validation.get_settings")
    def test_past_date_blocked(self, mock_settings):
        mock_settings.return_value = self._make_settings(allow_past=0)
        from finstein_hrms.server_script.leave_validation import validate_leave_dates

        doc = self._make_doc(from_date="2020-01-01", to_date="2020-01-01")
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_leave_dates(doc, None)

    @patch("finstein_hrms.server_script.leave_validation.get_settings")
    def test_future_date_passes(self, mock_settings):
        mock_settings.return_value = self._make_settings()
        from finstein_hrms.server_script.leave_validation import validate_leave_dates

        doc = self._make_doc()
        try:
            validate_leave_dates(doc, None)
        except frappe.exceptions.ValidationError:
            self.fail("Valid future date raised ValidationError unexpectedly.")

    @patch("finstein_hrms.server_script.leave_validation.get_settings")
    def test_exceeds_max_continuous_days(self, mock_settings):
        mock_settings.return_value = self._make_settings(max_days=3)
        from finstein_hrms.server_script.leave_validation import validate_leave_dates

        start = frappe.utils.add_days(frappe.utils.today(), 3)
        end = frappe.utils.add_days(frappe.utils.today(), 10)
        doc = self._make_doc(from_date=start, to_date=end)
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_leave_dates(doc, None)

    @patch("finstein_hrms.server_script.leave_validation.get_settings")
    def test_invalid_time_range_blocked(self, mock_settings):
        mock_settings.return_value = self._make_settings()
        from finstein_hrms.server_script.leave_validation import validate_leave_dates

        future = frappe.utils.add_days(frappe.utils.today(), 2)
        doc = self._make_doc(
            from_date=future,
            to_date=future,
            from_time="17:00:00",
            to_time="09:00:00",
        )
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_leave_dates(doc, None)

    @patch("finstein_hrms.server_script.leave_validation.get_settings")
    @patch("frappe.db.get_value")
    def test_insufficient_balance_blocked(self, mock_db, mock_settings):
        mock_settings.return_value = self._make_settings(balance_check=1)
        mock_db.return_value = {
            "total_leaves_allocated": 2,
            "total_leaves_taken": 1,
        }
        from finstein_hrms.server_script.leave_validation import check_leave_balance

        future = frappe.utils.add_days(frappe.utils.today(), 2)
        end = frappe.utils.add_days(frappe.utils.today(), 7)
        doc = self._make_doc(from_date=future, to_date=end)
        settings = mock_settings.return_value
        with self.assertRaises(frappe.exceptions.ValidationError):
            check_leave_balance(doc, settings)
