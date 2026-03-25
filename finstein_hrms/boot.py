# -----------------------------------------------
# FILE: your_app/boot.py
# PURPOSE: Extend frappe.boot with custom data for navbar
# DOCS: https://docs.frappe.io/framework/v15/user/en/python-api/hooks#extend-bootinfo
# -----------------------------------------------
import frappe


def add_navbar_data(bootinfo):
    """
    This method is called after login.
    All values added here are available in JS as frappe.boot.<key>
    Use this to pass data to navbar JS without extra API calls.
    """
    # Add company name for navbar display
    bootinfo.company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Your Company"

    # Add current user's full name
    bootinfo.user_fullname = frappe.db.get_value(
        "User", frappe.session.user, "full_name"
    ) or frappe.session.user

    # Add any custom flag/data your navbar needs
    bootinfo.custom_navbar = {
        "show_tasks": True,
        "show_calendar": True,
        "show_datetime": True,
    }

    # Filter workspace sidebar for pure Employee users
    roles = frappe.get_roles()
    privileged_roles = {"HR Manager", "Head", "System Manager", "Administrator", "Workspace Manager"}

    if "Employee" in roles and not privileged_roles.intersection(roles):
        allowed = {"Employee Workspace"}
        if hasattr(bootinfo, "allowed_workspaces") and bootinfo.allowed_workspaces:
            bootinfo.allowed_workspaces = [
                ws for ws in bootinfo.allowed_workspaces
                if ws.get("name") in allowed or ws.get("title") in allowed
            ]