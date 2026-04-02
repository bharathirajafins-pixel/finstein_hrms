from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeSeparation(FrappeTestCase):
    """Tests for employee_separation_validation.py business rules."""

    def _make_doc(self, workflow_state, name="SEP-TEST-0000"):
        doc = MagicMock()
        doc.name = name
        doc.employee = "_Test Employee"
        doc.workflow_state = workflow_state
        doc.is_new.return_value = False
        return doc

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_approval_sets_employee_left(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = self._make_doc("Approved", "SEP-TEST-0001")

        on_update(doc, None)
        mock_set_value.assert_any_call("Employee", "_Test Employee", "status", "Left")

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_non_approved_state_does_nothing(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = self._make_doc("Pending HR Approval", "SEP-TEST-0002")

        on_update(doc, None)
        mock_set_value.assert_not_called()

    @patch("frappe.db.set_value")
    @patch("frappe.get_doc")
    def test_approval_disables_user(self, mock_get_doc, mock_set_value):
        from finstein_hrms.server_script.employee_separation_validation import on_update

        doc = self._make_doc("Approved", "SEP-TEST-0003")

        on_update(doc, None)
        mock_set_value.assert_any_call(
            "User",
            mock_get_doc.return_value.user_id,
            "enabled",
            0,
        )

    @patch("frappe.db.get_value", return_value="Draft")
    def test_skip_to_ceo_stage_is_blocked(self, mock_get_value):
        from finstein_hrms.server_script.employee_separation_validation import validate

        doc = self._make_doc("Pending CEO Approval", "SEP-TEST-0004")

        with self.assertRaises(frappe.exceptions.ValidationError):
            validate(doc, None)

    @patch("frappe.db.get_value", return_value="Pending TL Approval")
    def test_tl_approval_can_move_to_ceo_stage(self, mock_get_value):
        from finstein_hrms.server_script.employee_separation_validation import validate

        doc = self._make_doc("Pending CEO Approval", "SEP-TEST-0005")

        try:
            validate(doc, None)
        except frappe.exceptions.ValidationError:
            self.fail("Valid TL to CEO transition raised ValidationError unexpectedly.")

    @patch("frappe.db.get_value", return_value="Pending CEO Approval")
    def test_hr_cannot_approve_before_ceo_to_hr_stage(self, mock_get_value):
        from finstein_hrms.server_script.employee_separation_validation import validate

        doc = self._make_doc("Approved", "SEP-TEST-0006")

        with self.assertRaises(frappe.exceptions.ValidationError):
            validate(doc, None)
