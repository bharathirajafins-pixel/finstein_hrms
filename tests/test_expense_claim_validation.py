from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class _Doc:
	def __init__(self, *, is_new=False, name="HR-EXP-0001"):
		self._is_new = is_new
		self.name = name

	def is_new(self):
		return self._is_new


class TestExpenseClaimValidation(FrappeTestCase):
	@patch("frappe.db.get_value")
	def test_new_doc_is_not_blocked(self, mock_get_value):
		from finstein_hrms.server_script.expense_claim_validation import validate_expense_claim_update

		validate_expense_claim_update(_Doc(is_new=True))
		mock_get_value.assert_not_called()

	@patch("frappe.get_roles", return_value=["Employee"])
	@patch("frappe.db.get_value")
	def test_employee_cannot_edit_pending_approval_claim(self, mock_get_value, mock_roles):
		from finstein_hrms.server_script.expense_claim_validation import validate_expense_claim_update

		mock_get_value.side_effect = [
			frappe._dict(employee="HR-EMP-00001", workflow_state="Pending Approval"),
			"employee@example.com",
		]

		with patch.object(frappe.session, "user", "employee@example.com"):
			with self.assertRaises(frappe.exceptions.ValidationError):
				validate_expense_claim_update(_Doc())

	@patch("frappe.get_roles", return_value=["Employee", "HR Manager"])
	@patch("frappe.db.get_value")
	def test_hr_manager_employee_is_not_blocked(self, mock_get_value, mock_roles):
		from finstein_hrms.server_script.expense_claim_validation import validate_expense_claim_update

		mock_get_value.side_effect = [
			frappe._dict(employee="HR-EMP-00001", workflow_state="Pending Approval"),
			"employee@example.com",
		]

		with patch.object(frappe.session, "user", "employee@example.com"):
			validate_expense_claim_update(_Doc())

	@patch("frappe.db.get_value")
	def test_other_workflow_state_is_not_blocked(self, mock_get_value):
		from finstein_hrms.server_script.expense_claim_validation import validate_expense_claim_update

		mock_get_value.return_value = frappe._dict(
			employee="HR-EMP-00001", workflow_state="Rejected"
		)

		validate_expense_claim_update(_Doc())

	@patch("frappe.get_roles", return_value=["Employee"])
	@patch("frappe.db.get_value")
	def test_non_owner_user_is_not_blocked(self, mock_get_value, mock_roles):
		from finstein_hrms.server_script.expense_claim_validation import validate_expense_claim_update

		mock_get_value.side_effect = [
			frappe._dict(employee="HR-EMP-00001", workflow_state="Pending Approval"),
			"owner@example.com",
		]

		with patch.object(frappe.session, "user", "other@example.com"):
			validate_expense_claim_update(_Doc())
