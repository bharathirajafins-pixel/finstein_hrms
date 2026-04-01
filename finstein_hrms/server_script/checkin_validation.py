"""Server-side validation and attendance sync for Employee Checkin."""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, get_time, getdate, time_diff_in_hours

from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import (
	get_settings,
)


def validate_checkin(doc, method=None):
	"""Validate employee check-in sequencing and policy rules."""
	settings = get_settings()

	_restrict_administrator_checkin()
	_mandatory(doc)
	_no_duplicate(doc)
	_ensure_checkout_has_checkin(doc)
	_checkout_order(doc)
	_min_hours(doc, settings)
	_calc_hours(doc)
	_set_status(doc, settings)
	_validate_timesheet_submission_before_checkout(doc)


def sync_attendance_from_checkin(doc, method=None):
	"""Create or update Attendance once check-out is completed."""
	if doc.employee and doc.time and not doc.checkout_time:
		ensure_timesheet_for_checkin(doc.name)
		return

	if not (doc.employee and doc.time and doc.checkout_time):
		return

	attendance_date = getdate(doc.time)
	status = (doc.attendance_status or "").strip() or "Absent"

	existing = frappe.db.exists(
		"Attendance",
		{
			"employee": doc.employee,
			"attendance_date": attendance_date,
			"docstatus": ("!=", 2),
		},
	)

	if existing:
		att = frappe.get_doc("Attendance", existing)
		if att.docstatus == 1:
			frappe.db.set_value("Attendance", existing, "status", status)
		else:
			att.status = status
			att.flags.ignore_validate = True
			att.save(ignore_permissions=True)
			att.submit()
	else:
		att = frappe.new_doc("Attendance")
		att.employee = doc.employee
		att.attendance_date = attendance_date
		att.status = status
		att.flags.ignore_validate = True
		att.insert(ignore_permissions=True)
		att.submit()

	tag_attendance_anomalies(doc)
	calculate_and_store_overtime(doc.employee, attendance_date, float(doc.working_hours or 0))


@frappe.whitelist()
def ensure_timesheet_for_checkin(checkin_name):
	"""Create and link a draft Timesheet for an Employee Checkin if missing."""
	if not checkin_name:
		frappe.throw(_("Employee Checkin is required."))

	doc = frappe.get_doc("Employee Checkin", checkin_name)
	if getattr(doc, "timesheet", None):
		payload = _get_timesheet_payload(doc.timesheet)
		if payload["docstatus"] != 2:
			return payload

	if not (doc.employee and doc.time):
		frappe.throw(_("Check-In must be saved before creating a timesheet."))

	ts = frappe.new_doc("Timesheet")
	ts.employee = doc.employee
	ts.start_date = getdate(doc.time)
	ts.end_date = getdate(doc.time)
	ts.append(
		"time_logs",
		{
			"from_time": doc.time,
			"to_time": doc.time,
			"hours": 0,
		},
	)
	ts.insert(ignore_permissions=True)

	frappe.db.set_value("Employee Checkin", doc.name, "timesheet", ts.name, update_modified=False)
	return {"timesheet": ts.name, "docstatus": ts.docstatus}


@frappe.whitelist()
def validate_timesheet_before_checkout(checkin_name):
	"""Return linked Timesheet readiness for the checkout UI flow."""
	if not checkin_name:
		frappe.throw(_("Employee Checkin is required."))

	doc = frappe.get_doc("Employee Checkin", checkin_name)
	if not getattr(doc, "timesheet", None):
		return {"ready": False, "timesheet": None, "message": _timesheet_required_message()}

	payload = _get_timesheet_payload(doc.timesheet)
	payload["ready"] = _is_timesheet_ready_for_checkout(doc.timesheet)
	payload["message"] = None if payload["ready"] else _timesheet_required_message()
	return payload


def tag_attendance_anomalies(doc):
	"""
	Tag linked Attendance as late entry or early exit based on settings.
	"""
	settings = get_settings()
	attendance_date = getdate(doc.time) if doc.time else None
	if not attendance_date:
		return

	attendance_name = frappe.db.get_value(
		"Attendance",
		{
			"employee": doc.employee,
			"attendance_date": attendance_date,
			"docstatus": 1,
		},
		"name",
	)
	if not attendance_name:
		return

	if settings.enable_late_entry_tagging and settings.shift_start_time and doc.time:
		checkin_time = get_time(doc.time)
		shift_start = get_time(settings.shift_start_time)
		if checkin_time > shift_start:
			frappe.db.set_value("Attendance", attendance_name, "custom_late_entry", 1)
			frappe.logger().info(f"[Checkin] Late entry tagged for {doc.employee} on {attendance_date}")

	if settings.enable_early_exit_tagging and settings.shift_end_time and doc.checkout_time:
		checkout_time = get_time(doc.checkout_time)
		shift_end = get_time(settings.shift_end_time)
		if checkout_time < shift_end:
			frappe.db.set_value("Attendance", attendance_name, "custom_early_exit", 1)
			frappe.logger().info(f"[Checkin] Early exit tagged for {doc.employee} on {attendance_date}")


def calculate_and_store_overtime(employee, attendance_date, worked_hours):
	"""
	Calculate and store overtime in Attendance when worked hours exceed standard.
	"""
	settings = get_settings()
	if not settings.enable_overtime_tracking:
		return

	standard = settings.min_checkin_hours or 8.0
	if worked_hours <= standard:
		return

	overtime = round(worked_hours - standard, 2)
	attendance_name = frappe.db.get_value(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": attendance_date,
			"docstatus": 1,
		},
		"name",
	)
	if attendance_name:
		frappe.db.set_value(
			"Attendance",
			attendance_name,
			"custom_overtime_hours",
			overtime,
		)
		frappe.logger().info(f"[Overtime] {employee} logged {overtime}h overtime on {attendance_date}")


def _mandatory(doc):
	"""Ensure mandatory check-in fields are present."""
	if not doc.employee:
		frappe.throw(_("Employee is mandatory."))
	if not doc.time:
		frappe.throw(_("Check-In Time is mandatory."))


def _restrict_administrator_checkin():
	"""
	Restrict self check-in / check-out actions to employee users.
	Admin and HR roles should not manually create or update these records.
	"""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return

	roles = set(frappe.get_roles() or [])
	restricted_roles = {"System Manager", "HR Manager", "HR User", "Head"}

	if frappe.session.user == "Administrator" or roles.intersection(restricted_roles):
		frappe.throw(
			_(
				"Employee Checkin can only be created through the employee Check In / "
				"Check Out flow. Administrator and HR roles cannot create or update "
				"check-in records manually."
			)
		)


def _no_duplicate(doc):
	"""Prevent multiple check-in documents for the same employee and date."""
	date_value = getdate(doc.time)
	if getattr(doc, "log_type", "IN") != "IN":
		return

	start_of_day = f"{date_value} 00:00:00"
	end_of_day = f"{date_value} 23:59:59"

	existing = frappe.db.exists(
		"Employee Checkin",
		{
			"employee": doc.employee,
			"name": ("!=", doc.name),
			"time": ("between", [start_of_day, end_of_day]),
		},
	)

	if existing:
		frappe.throw(
			_(
				"Check-In already exists for <b>{0}</b> on <b>{1}</b>. "
				"Please open the existing record: <b>{2}</b>"
			).format(doc.employee_name or doc.employee, date_value, existing)
		)


def _ensure_checkout_has_checkin(doc):
	"""For OUT logs, ensure there is a prior IN check-in on the same day."""
	if getattr(doc, "log_type", "IN") != "OUT":
		return

	date_value = getdate(doc.time)
	start_of_day = f"{date_value} 00:00:00"
	end_of_day = f"{date_value} 23:59:59"

	prior_checkin = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": doc.employee,
			"log_type": "IN",
			"time": ("between", [start_of_day, end_of_day]),
			"name": ("!=", doc.name),
		},
		"name",
	)
	if not prior_checkin:
		frappe.throw("Cannot check out without a prior check-in for the day.")


def _checkout_order(doc):
	"""Ensure checkout is after check-in and not set without check-in."""
	if doc.checkout_time and not doc.time:
		frappe.throw(_("Check-In must be set before Check-Out."))

	if doc.checkout_time and doc.time:
		if get_datetime(doc.checkout_time) <= get_datetime(doc.time):
			frappe.throw(_("Check-Out Time must be after Check-In Time."))


def _min_hours(doc, settings):
	"""Enforce minimum working hours before normal checkout."""
	if not (doc.checkout_time and doc.time):
		return

	is_privileged = any(role in frappe.get_roles() for role in ["HR Manager", "System Manager"])
	is_force = getattr(doc, "checkout_type", "") == "Force"

	if is_force and not settings.enable_force_checkout:
		frappe.throw("Force checkout is disabled in Finstein HRMS Settings.")

	if is_force or is_privileged:
		return

	total = time_diff_in_hours(get_datetime(doc.checkout_time), get_datetime(doc.time))
	break_hours = float(getattr(doc, "break_hours", 0) or 0)
	worked = max(total - break_hours, 0)

	min_hours = float(settings.min_checkin_hours or 8.0)
	if worked < min_hours:
		frappe.throw(
			_("Minimum {0} working hours are required before checkout. Current: <b>{1} hrs</b>.").format(
				min_hours, round(worked, 2)
			)
		)


def _calc_hours(doc):
	"""Compute net working hours after break deduction."""
	if doc.time and doc.checkout_time:
		total = time_diff_in_hours(get_datetime(doc.checkout_time), get_datetime(doc.time))
		break_hours = float(getattr(doc, "break_hours", 0) or 0)
		doc.working_hours = round(max(total - break_hours, 0), 2)
	else:
		doc.working_hours = None


def _set_status(doc, settings):
	"""Set attendance status based on calculated working hours."""
	if not doc.checkout_time:
		return

	worked = float(doc.working_hours or 0)
	min_hours = float(settings.min_checkin_hours or 8.0)
	half_day_hours = min_hours / 2.0

	if worked >= min_hours:
		doc.attendance_status = "Present"
	elif worked >= half_day_hours:
		doc.attendance_status = "Half Day"
	else:
		doc.attendance_status = "Absent"


def _validate_timesheet_submission_before_checkout(doc):
	"""Require a completed saved or submitted linked timesheet before checkout."""
	if not doc.checkout_time:
		return

	timesheet_name = getattr(doc, "timesheet", None)
	if not timesheet_name:
		frappe.throw(_timesheet_required_message())

	if not _is_timesheet_ready_for_checkout(timesheet_name):
		frappe.throw(_timesheet_required_message())


def _timesheet_required_message():
	return _("Please complete and save your timesheet before checking out.")


def _get_timesheet_payload(timesheet_name):
	"""Return lightweight Timesheet status payload for client flow control."""
	ts = frappe.db.get_value("Timesheet", timesheet_name, ["name", "docstatus"], as_dict=True)
	if not ts:
		return {"timesheet": timesheet_name, "docstatus": 2}

	return {"timesheet": ts.name, "docstatus": ts.docstatus}


def _is_timesheet_ready_for_checkout(timesheet_name):
	"""Allow checkout when linked timesheet is saved/submitted with meaningful rows."""
	if not timesheet_name:
		return False

	try:
		ts = frappe.get_doc("Timesheet", timesheet_name)
	except frappe.DoesNotExistError:
		return False

	if ts.docstatus == 2:
		return False

	return _has_checkout_ready_time_logs(ts)


def _has_checkout_ready_time_logs(timesheet):
	"""A draft Timesheet is checkout-ready once at least one real row has Activity Type."""
	for row in timesheet.get("time_logs") or []:
		has_any_data = bool(row.activity_type or row.from_time or row.to_time or flt(row.hours))
		if not has_any_data:
			continue

		if row.activity_type and row.from_time:
			return True

	return False
