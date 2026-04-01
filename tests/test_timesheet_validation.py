from frappe.tests.utils import FrappeTestCase


class _Doc:
	def __init__(self, *, is_new=False, docstatus=0, employee_saved_draft=0):
		self._is_new = is_new
		self.docstatus = docstatus
		self.employee_saved_draft = employee_saved_draft

	def is_new(self):
		return self._is_new


class TestTimesheetValidation(FrappeTestCase):
	def test_existing_draft_is_marked_as_saved(self):
		from finstein_hrms.server_script.timesheet_validation import mark_employee_saved_draft

		doc = _Doc()
		mark_employee_saved_draft(doc)
		self.assertEqual(doc.employee_saved_draft, 1)

	def test_new_draft_is_not_marked_as_saved(self):
		from finstein_hrms.server_script.timesheet_validation import mark_employee_saved_draft

		doc = _Doc(is_new=True)
		mark_employee_saved_draft(doc)
		self.assertEqual(doc.employee_saved_draft, 0)

	def test_submitted_timesheet_is_not_marked_as_saved(self):
		from finstein_hrms.server_script.timesheet_validation import mark_employee_saved_draft

		doc = _Doc(docstatus=1)
		mark_employee_saved_draft(doc)
		self.assertEqual(doc.employee_saved_draft, 0)
