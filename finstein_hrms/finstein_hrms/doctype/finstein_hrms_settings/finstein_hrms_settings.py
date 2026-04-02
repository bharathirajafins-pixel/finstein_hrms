import frappe
from frappe.model.document import Document


class FinsteinHRMSSettings(Document):
	"""
	Single DocType that stores all configurable business rules
	for the Finstein HRMS application.
	HR Managers can change rules from the UI without code changes.
	"""

	pass


def get_settings():
	"""
    Central helper used by all validation modules.
    Returns the single Finstein HRMS Settings document.

    Usage in any validation file:
        from finstein_hrms.finstein_hrms.doctype\
            .finstein_hrms_settings.finstein_hrms_settings import get_settings
        settings = get_settings()
    """
	return frappe.get_single("Finstein HRMS Settings")
