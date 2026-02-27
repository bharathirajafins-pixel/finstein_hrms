import frappe
from frappe import _


def validate_interview_scheduling(doc, method):
    """
    Validate interview scheduling with multiple checks:
    1. Scheduled date validation (cannot be past date)
    2. Time validation (from_time and to_time)
    3. Prevent duplicate interviews for the same round
    4. Round order validation - enforce sequential scheduling
    5. Check previous round status before scheduling next round

    Note: Validations only apply to regular users (non-admin / non-System Manager)
    Uses custom field: custom_interview_type
    """

    # -----------------------------------------------
    # 🔐 Skip validations for Administrator / System Manager
    # -----------------------------------------------
    if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles(frappe.session.user):
        return

    # -----------------------------------------------
    # 🔍 Guard: Ensure required fields are present
    # -----------------------------------------------
    if not doc.interview_round or not doc.job_applicant or not doc.scheduled_on:
        frappe.throw(_("Interview Round, Job Applicant, and Scheduled Date are required."))

    if not doc.from_time or not doc.to_time:
        frappe.throw(_("From Time and To Time are required fields."))

    # Validate custom_interview_type is set
    if not doc.custom_interview_type:
        frappe.throw(_("Interview Type is required. Please select an Interview Type before saving."))

    # Validate that the selected Interview Round belongs to the selected Interview Type
    round_interview_type = frappe.db.get_value(
        "Interview Round",
        doc.interview_round,
        "interview_type"
    )
    if round_interview_type and round_interview_type != doc.custom_interview_type:
        frappe.throw(
            _("Interview Round '{0}' does not belong to Interview Type '{1}'. "
              "Please select a matching Interview Round.").format(
                doc.interview_round, doc.custom_interview_type
            )
        )

    # -----------------------------------------------
    # 1️⃣ Validate Scheduled Date
    # -----------------------------------------------
    scheduled_date = frappe.utils.getdate(doc.scheduled_on)
    current_date = frappe.utils.getdate(frappe.utils.today())

    if scheduled_date < current_date:
        frappe.throw(
            _("Scheduled Date cannot be a past date. "
              "Please select today or a future date.")
        )

    # -----------------------------------------------
    # 2️⃣ Validate From Time and To Time
    # -----------------------------------------------
    from_time_str = frappe.utils.get_time_str(doc.from_time)
    to_time_str = frappe.utils.get_time_str(doc.to_time)

    # Always validate: To Time must be greater than From Time
    if to_time_str <= from_time_str:
        frappe.throw(
            _("To Time must be greater than From Time. "
              "Please select a valid time range.")
        )

    # If scheduled for today, also validate against current time
    if scheduled_date == current_date:
        now_str = frappe.utils.nowtime()

        if from_time_str < now_str:
            frappe.throw(
                _("From Time cannot be a past time for today. "
                  "Please select a current or future From Time.")
            )

        if to_time_str < now_str:
            frappe.throw(
                _("To Time cannot be a past time for today. "
                  "Please select a current or future To Time.")
            )

    # -----------------------------------------------
    # 3️⃣ Prevent Duplicate Interviews Per Round
    # -----------------------------------------------
    filters = {
        "job_applicant": doc.job_applicant,
        "interview_round": doc.interview_round,
        "docstatus": ["!=", 2]  # Exclude cancelled documents
    }

    # Exclude current doc when editing
    if doc.name:
        filters["name"] = ["!=", doc.name]

    existing_interview = frappe.db.get_value(
        "Interview",
        filters,
        ["name", "status"],
        as_dict=True
    )

    if existing_interview:
        frappe.throw(
            _("An interview for round '{0}' already exists for this job applicant.\n"
              "Existing Interview: {1}\n"
              "Current Status: {2}\n"
              "Only one interview per round is allowed.").format(
                doc.interview_round,
                existing_interview.name,
                existing_interview.status or "Pending"
            )
        )

    # -----------------------------------------------
    # 4️⃣ & 5️⃣ Validate Round Order + Previous Round Statuses
    # -----------------------------------------------
    round_order = frappe.db.get_value(
        "Interview Round",
        doc.interview_round,
        "round_order"
    )

    if not round_order:
        frappe.throw(
            _("Round order is not defined for Interview Round: '{0}'. "
              "Please configure the round order before scheduling.").format(doc.interview_round)
        )

    # First round — no previous rounds to check
    if round_order == 1:
        return

    # Check all previous rounds sequentially
    for prev_round_num in range(1, round_order):

        # Get previous round name by order number
        prev_round_name = frappe.db.get_value(
            "Interview Round",
            {
                "round_order": prev_round_num,
                "interview_type": doc.custom_interview_type  # Filter by same interview type
            },
            "name"
        )

        if not prev_round_name:
            frappe.throw(
                _("Interview Round with order {0} under Interview Type '{1}' is not found. "
                  "Please ensure all rounds are configured sequentially.").format(
                    prev_round_num, doc.custom_interview_type
                )
            )

        # Get previous interview for this applicant
        prev_interview = frappe.db.get_value(
            "Interview",
            {
                "job_applicant": doc.job_applicant,
                "interview_round": prev_round_name,
                "docstatus": ["!=", 2]
            },
            ["name", "status"],
            as_dict=True
        )

        # Previous round not scheduled at all
        if not prev_interview:
            frappe.throw(
                _("Round {0} ({1}) has not been scheduled yet for this applicant.\n"
                  "Please schedule and complete all previous rounds before proceeding.").format(
                    prev_round_num, prev_round_name
                )
            )

        # Previous round is still pending
        if prev_interview.status == "Pending":
            frappe.throw(
                _("Cannot schedule Round {0}.\n"
                  "Previous Round {1} ({2}) is still Pending.\n"
                  "Please complete the previous round first.").format(
                    round_order, prev_round_num, prev_round_name
                )
            )

        # Previous round was rejected — stop the process
        if prev_interview.status == "Rejected":
            frappe.throw(
                _("Cannot schedule Round {0}.\n"
                  "The applicant was Rejected in Round {1} ({2}).\n"
                  "Interview process cannot continue for this applicant.").format(
                    round_order, prev_round_num, prev_round_name
                )
            )

        # Previous round must be Cleared to proceed
        if prev_interview.status != "Cleared":
            frappe.throw(
                _("Cannot schedule Round {0}.\n"
                  "Round {1} ({2}) has status: '{3}'.\n"
                  "All previous rounds must be 'Cleared' before scheduling the next round.").format(
                    round_order, prev_round_num, prev_round_name,
                    prev_interview.status or "Pending"
                )
            )