import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock


class TestEmployeeSeparation(FrappeTestCase):
    """Tests for employee_separation_validation.py business rules."""

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_approval_sets_employee_left(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = MagicMock()
        doc.workflow_state = "Approved"
        doc.employee = "_Test Employee"
        doc.name = "SEP-TEST-0001"

        on_update(doc, None)
        mock_set_value.assert_any_call("Employee", "_Test Employee", "status", "Left")

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_non_approved_state_does_nothing(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = MagicMock()
        doc.workflow_state = "Pending HR Approve"
        doc.employee = "_Test Employee"
        doc.name = "SEP-TEST-0002"

        on_update(doc, None)
        mock_set_value.assert_not_called()

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_approval_disables_user(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = MagicMock()
        doc.workflow_state = "Approved"
        doc.employee = "_Test Employee"
        doc.name = "SEP-TEST-0003"

        on_update(doc, None)
        mock_set_value.assert_any_call(
            "User",
            mock_get_doc.return_value.user_id,
            "enabled",
            0,
        )
