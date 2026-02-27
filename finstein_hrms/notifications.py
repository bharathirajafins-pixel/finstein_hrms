# -----------------------------------------------
# FILE: your_app/notifications.py
# PURPOSE: Customize the bell icon notification dropdown
# DOCS: https://docs.frappe.io/framework/v15/user/en/python-api/hooks#notification-configurations
# -----------------------------------------------


def get_config():
    """
    Controls what appears in the notification (bell icon) dropdown.
    Three sections:
    - for_doctype: show unread count for specific doctypes with filters
    - for_module_doctypes: maps doctypes to module names
    - for_module: maps modules to functions that return unread counts
    """
    return {
        # Show unread count for these doctypes with status filter
        "for_doctype": {
            "Interview": {"status": "Pending"},         # Pending interviews
            "Job Applicant": {"status": "Open"},        # Open job applicants
            "ToDo": {"status": "Open"},                 # Open to-dos
        },

        # Map these doctypes to their module display names
        "for_module_doctypes": {
            "ToDo": "To Do",
            "Event": "Calendar",
            "Comment": "Messages",
        },

        # Map modules to functions that return their unread count
        "for_module": {
            "To Do": "frappe.core.notifications.get_things_todo",
            "Calendar": "frappe.core.notifications.get_todays_events",
            "Messages": "frappe.core.notifications.get_unread_messages",
        }
    }