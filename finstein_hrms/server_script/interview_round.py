import frappe
from frappe import _


def validate_interview_scheduling(doc, method):
    """
    Validate interview scheduling with multiple checks:
    1. Scheduled date validation
    2. Time validation (from_time and to_time)
    3. Round order validation
    4. Prevent duplicate interviews for the same round
    5. Check previous round status before scheduling next round
    
    Note: Validations only apply to regular users (non-admin)
    """
    
    # Check if current user is admin - admins can bypass validations
    if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles(frappe.session.user):
        return
    
    # # Skip validation if required fields are not filled
    # if not doc.interview_round or not doc.job_applicant or not doc.scheduled_on:
    #     return
    
    # -----------------------------------
    # 1️⃣ Validate Scheduled Date Only
    # -----------------------------------
    
    scheduled_date = frappe.utils.getdate(doc.scheduled_on)
    current_date = frappe.utils.getdate(frappe.utils.today())
    
    if scheduled_date < current_date:
        frappe.throw(
            _("Scheduled Date cannot be a past date. "
              "Please select today or a future date.")
        )
    
    # -----------------------------------
    # 2️⃣ Validate From Time and To Time
    # -----------------------------------
    
    if scheduled_date == current_date:
        now_str = frappe.utils.nowtime()
        from_time_str = frappe.utils.get_time_str(doc.from_time)
        to_time_str = frappe.utils.get_time_str(doc.to_time)
        
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
        
        if to_time_str <= from_time_str:
            frappe.throw(
                _("To Time must be greater than From Time. "
                  "Please select a valid time range.")
            )
    
    # -----------------------------------
    # 3️⃣ Validate Round Order
    # -----------------------------------
    
    # Get selected round order
    round_order = frappe.db.get_value(
        "Interview Round",
        doc.interview_round,
        "round_order"
    )
    
    if not round_order:
        frappe.throw(_("Round order not defined for this Interview Round."))
    
    # Allow first round
    if round_order != 1:
        # Check all previous rounds
        for prev_round_num in range(1, round_order):
            # Get previous round name
            prev_round_name = frappe.db.get_value(
                "Interview Round",
                {"round_order": prev_round_num},
                "name"
            )
            
            if not prev_round_name:
                frappe.throw(
                    _("Interview Round with order {0} not found.").format(prev_round_num)
                )
            
            # Check previous interview
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
            
            if not prev_interview:
                frappe.throw(
                    _("Round {0} ({1}) has not been scheduled yet.").format(
                        prev_round_num, prev_round_name
                    )
                )
            
            if prev_interview.status != "Cleared":
                frappe.throw(
                    _("Round {0} ({1}) is not cleared yet.\n"
                      "Current Status: {2}.\n"
                      "Please clear all previous rounds before scheduling this round.").format(
                        prev_round_num, prev_round_name, prev_interview.status or 'Pending'
                    )
                )
    
    # -----------------------------------
    # 4️⃣ Prevent Duplicate Interviews Per Round
    # -----------------------------------
    # A user should only create one interview per round.
    # Reject creation if an interview already exists for this round.
    
    existing_interview = frappe.db.get_value(
        "Interview",
        {
            "job_applicant": doc.job_applicant,
            "interview_round": doc.interview_round,
            "docstatus": ["!=", 2]  # Exclude cancelled documents
        },
        ["name", "status"],
        as_dict=True
    )
    
    if existing_interview:
        frappe.throw(
            _("An interview for round '{0}' already exists for this job applicant.\n"
              "Current Status: {1}\n"
              "You can only create one interview per round.").format(
                doc.interview_round, existing_interview.status or 'Pending'
            )
        )
    
    # -----------------------------------
    # 5️⃣ Validate Previous Round Statuses
    # -----------------------------------
    # If any previous round has 'Pending' or 'Rejected' status,
    # prevent creation of next round interview
    
    if round_order != 1:
        for prev_round_num in range(1, round_order):
            prev_round_name = frappe.db.get_value(
                "Interview Round",
                {"round_order": prev_round_num},
                "name"
            )
            
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
            
            if prev_interview:
                if prev_interview.status == "Pending":
                    frappe.throw(
                        _("Cannot schedule round {0}.\n"
                          "Previous round ({1}) is still Pending.\n"
                          "Please complete the previous round first.").format(
                            round_order, prev_round_num
                        )
                    )
                
                if prev_interview.status == "Rejected":
                    frappe.throw(
                        _("Cannot schedule round {0}.\n"
                          "You were rejected in a previous round ({1}).\n"
                          "Interview process cannot continue.").format(
                            round_order, prev_round_num
                        )
                    )
