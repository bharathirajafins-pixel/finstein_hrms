app_name = "finstein_hrms"
app_title = "Finstein_hrms"
app_publisher = "finstein"
app_description = "hrms for the our company"
app_email = "bharathi7b650@gmail.com"
app_license = "mit"


# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "finstein_hrms",
# 		"logo": "/assets/finstein_hrms/logo.png",
# 		"title": "Finstein_hrms",
# 		"route": "/finstein_hrms",
# 		"has_permission": "finstein_hrms.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/finstein_hrms/css/finstein_hrms.css"
# app_include_js = "/assets/finstein_hrms/js/finstein_hrms.js"

# include js, css files in header of web template
# web_include_css = "/assets/finstein_hrms/css/finstein_hrms.css"
# web_include_js = "/assets/finstein_hrms/js/finstein_hrms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "finstein_hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "finstein_hrms/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "finstein_hrms.utils.jinja_methods",
# 	"filters": "finstein_hrms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "finstein_hrms.install.before_install"
# after_install = "finstein_hrms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "finstein_hrms.uninstall.before_uninstall"
# after_uninstall = "finstein_hrms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "finstein_hrms.utils.before_app_install"
# after_app_install = "finstein_hrms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "finstein_hrms.utils.before_app_uninstall"
# after_app_uninstall = "finstein_hrms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

notification_config = "finstein_hrms.notifications.get_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"finstein_hrms.tasks.all"
# 	],
# 	"daily": [
# 		"finstein_hrms.tasks.daily"
# 	],
# 	"hourly": [
# 		"finstein_hrms.tasks.hourly"
# 	],
# 	"weekly": [
# 		"finstein_hrms.tasks.weekly"
# 	],
# 	"monthly": [
# 		"finstein_hrms.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "finstein_hrms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "finstein_hrms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "finstein_hrms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["finstein_hrms.utils.before_request"]
# after_request = ["finstein_hrms.utils.after_request"]

# Extend frappe.boot with custom navbar data
# extend_bootinfo = "finstein_hrms.boot.add_navbar_data"

# Job Events
# ----------
# before_job = ["finstein_hrms.utils.before_job"]
# after_job = ["finstein_hrms.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"finstein_hrms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Custom HRMS portability hooks (exported customizations + meal QR automation)
fixtures = [
    {
        "doctype": "Workflow"
    },
    {
        "doctype": "Workflow State"
    },
    {
        "doctype": "Workflow Transition"
    }
    ]

doc_events = {
    "Food Count": {
        "after_insert": "finstein_hrms.scheduled_tasks.update_food_qr_count",
        "on_update": "finstein_hrms.scheduled_tasks.update_food_qr_count",
    },
    "Leave Application": {
        "validate": "finstein_hrms.server_script.leave_validation.validate"
    },
    "Employee Checkin": {
        "before_save": "finstein_hrms.server_script.checkin_validation.validate_checkin",
        "after_insert": "finstein_hrms.server_script.checkin_validation.sync_attendance_from_checkin",
        "on_update": "finstein_hrms.server_script.checkin_validation.sync_attendance_from_checkin",
    },
    "Attendance Request": {
        "validate": "finstein_hrms.server_script.attendance_request_validation.validate_attendance_request"
    },
    "Interview": {
        "validate": "finstein_hrms.server_script.interview_round.validate_interview_scheduling"
    },
    "Employee Separation": {
        "on_update": "finstein_hrms.server_script.employee_separation_validation.on_update"
    }
}

scheduler_events = {
    "daily": [
        "finstein_hrms.scheduled_tasks.create_food_qr_records",
    ],
    "cron": {
        "0 9 * * *": ["finstein_hrms.scheduled_tasks.activate_breakfast_qr"],
        "1 11 * * *": ["finstein_hrms.scheduled_tasks.mark_breakfast_not_consumed"],
        "30 12 * * *": ["finstein_hrms.scheduled_tasks.activate_lunch_qr"],
        "1 15 * * *": ["finstein_hrms.scheduled_tasks.mark_lunch_not_consumed"],
        "0 19 * * *": ["finstein_hrms.scheduled_tasks.activate_dinner_qr"],
        "1 22 * * *": ["finstein_hrms.scheduled_tasks.mark_dinner_not_consumed"],
    },
}

doctype_js = {
    "Employee Checkin": "public/js/employee_checkin_client.js",
    "Leave Application": "public/js/leave_application.js",
    "Employee Separation": "public/js/employee_separation.js",
    "Attendance Request"   : "public/js/attendance_request.js",
    "Expense Claim"      : "public/js/expense_claim.js",
    "Interview": "public/js/interview.js"
}



# Global includes: notification enhancements only
app_include_css = ["/assets/finstein_hrms/css/notification_theme.css"]
app_include_js = ["/assets/finstein_hrms/js/notification_popup.js"]
