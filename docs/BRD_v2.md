# Finstein HRMS - Business Requirements Document (BRD) v2

## 1. Document Overview

**Project Name:** Finstein HRMS
**Type:** Frappe/ERPNext Custom Extension App
**Version:** Current (develop branch)
**Tech Stack:** Python 3.10+ | Frappe Framework | MariaDB | Redis | Vanilla JS
**License:** MIT

### 1.1 Purpose
Finstein HRMS is a custom HRMS extension layer built on ERPNext that provides enhanced HR workflows for Finstein company. It extends standard ERPNext HR module with custom business rules, approval workflows, a QR-based meal ordering system, and configurable policy enforcement.

### 1.2 Stakeholders & Roles

| Role | Description | Key Capabilities |
|------|-------------|-----------------|
| **Employee** | Regular staff member | Self-service: checkin/checkout, leave applications, attendance requests, meal ordering, expense claims, separation requests |
| **Team Leader** | First-level approver | Approve/reject leave applications and attendance requests for team members |
| **HR Manager** | HR operations | Full HR operations: second-level approvals, employee management, payroll, settings configuration |
| **Head (CEO)** | Final authority | Final approval for separations, payroll entries, job requisitions; access to CEO dashboard |
| **Projects Manager** | Department head | Create job requisitions for hiring |
| **Food Provider** | Meal vendor | Manage food menu items |
| **System Manager** | IT admin | System configuration, user management |

---

## 2. Functional Requirements

### 2.1 Employee Check-In / Check-Out System

**Module:** `server_script/checkin_validation.py`, `public/js/employee_checkin_client.js`
**DocType:** Employee Checkin (extended)

#### 2.1.1 Business Rules

| # | Rule | Configurable | Setting |
|---|------|-------------|---------|
| 1 | Only employees can check in (Administrator, HR Manager, HR User, Head roles are blocked) | No | Hardcoded |
| 2 | Employee field is mandatory | No | - |
| 3 | Check-in time is mandatory | No | - |
| 4 | One check-in per employee per day (duplicate prevention) | No | - |
| 5 | Check-out requires a prior check-in on the same day | No | - |
| 6 | Check-out time must be after check-in time | No | - |
| 7 | Minimum working hours required before checkout | Yes | `min_checkin_hours` (default: 8.0) |
| 8 | Break hours deducted from total working hours | No | Calculated from break_start/break_end |
| 9 | Force checkout allowed (bypasses min hours) | Yes | `enable_force_checkout` (default: 1) |
| 10 | HR Manager / System Manager exempt from min hours | No | Hardcoded |

#### 2.1.2 Automatic Calculations

| Calculation | Formula | Stored In |
|------------|---------|-----------|
| Working Hours | (checkout_time - checkin_time) - break_hours | Employee Checkin.working_hours |
| Attendance Status | >= min_hours: Present; >= min/2: Half Day; else: Absent | Employee Checkin.attendance_status |
| Late Entry | checkin_time > shift_start_time | Attendance.custom_late_entry |
| Early Exit | checkout_time < shift_end_time | Attendance.custom_early_exit |
| Overtime | worked_hours - min_checkin_hours (if positive) | Attendance.custom_overtime_hours |

#### 2.1.3 Attendance Auto-Sync
- On check-out completion, system auto-creates or updates an **Attendance** record
- Status set based on worked hours calculation
- Attendance is automatically submitted (docstatus=1)
- Tags late entry and early exit anomalies based on shift times

#### 2.1.4 UI Behavior
- Dashboard shows current status: Not Checked In / Checked In / On Break / Checkout Complete
- Action buttons rendered dynamically: Check In, Check Out, Permission Check-In
- If checkout attempted before 8 hours: dialog offers "Force Checkout" or "Permission Checkout"
- Break start/end buttons for permission breaks
- device_id, shift, remarks fields are hidden

#### 2.1.5 Custom Fields on Employee Checkin

| Field | Type | Description |
|-------|------|-------------|
| checkout_time | Datetime | Out timestamp |
| log_type_out | Select | "OUT" or "FORCE OUT" |
| break_start | Datetime | Break start timestamp |
| break_end | Datetime | Break end timestamp |
| break_hours | Float | Total break duration in hours |
| working_hours | Float | Net working hours (bold, in list view) |
| attendance_status | Select | Present / Half Day / Absent / On Break |
| checkout_type | Select | Normal / Force |

---

### 2.2 Leave Application Management

**Module:** `server_script/leave_validation.py`, `public/js/leave_application.js`
**DocType:** Leave Application (extended)

#### 2.2.1 Business Rules

| # | Rule | Configurable | Setting |
|---|------|-------------|---------|
| 1 | From Date cannot be after To Date | No | - |
| 2 | Past date leave blocked (configurable) | Yes | `allow_past_date_leave` (default: 0) |
| 3 | Full-day leave for today only before cutoff time | Yes | `leave_submission_cutoff_time` (default: 17:00) |
| 4 | Half-day leave for today only before half-day cutoff | Yes | `half_day_cutoff_time` (default: 12:00) |
| 5 | Maximum continuous leave days per application | Yes | `max_continuous_leave_days` (default: 3) |
| 6 | Half-day leaves exempt from continuous day limit | No | - |
| 7 | Custom from_time must be before custom to_time | No | - |
| 8 | Leave balance checked on submission | Yes | `enable_leave_balance_check` (default: 1) |
| 9 | Active allocation must exist for leave type | No | Checked if balance check enabled |

#### 2.2.2 Approval Workflow

**Workflow Name:** "Leave Application Workflow"

```
                         ┌──────────────────────┐
                         │        Draft          │
                         │   (Employee edits)    │
                         └─────┬──────────┬──────┘
                               │          │
          Employee is NOT TL   │          │   Employee IS TL
          "Request to TL"      │          │   "Request to HR"
                               ▼          ▼
                    ┌──────────────┐  ┌──────────────────┐
                    │   Pending    │  │ Pending HR Approve│
                    │ (TL reviews) │  │  (HR reviews)     │
                    └──┬───────┬──┘  └────────┬──────────┘
                       │       │              │
          "Reject"     │       │ "Verify      │ "Approve"
                       ▼       │  &Forward"   ▼
              ┌────────────┐   │    ┌──────────────┐
              │Rejected    │   └───►│Approved by HR│
              │by TL       │        │  (Submitted) │
              └────────────┘        └──────────────┘
```

**Transition Conditions:**
- "Request to TL": Employee is NOT a Team Leader
- "Request to HR" (direct): Employee IS a Team Leader
- "Reject" / "Verify&Forward": `frappe.session.user == doc.leave_approver`
- "Approve": HR Manager (no additional condition)

#### 2.2.3 Leave Withdrawal
- Available when workflow_state is "Pending" or "Pending HR Approve"
- Only document owner can withdraw
- Resets workflow_state to "Draft"
- Controlled by `enable_leave_withdrawal` setting
- API: `withdraw_leave_application(docname)`

#### 2.2.4 Notifications

| Notification | Trigger | Recipient | Channel |
|-------------|---------|-----------|---------|
| Leave Application Pending TL Approval | Save, workflow_state="Pending" | leave_approver | System |
| Leave Application Pending HR Approval | Save, workflow_state="Pending HR Approve" | HR Manager role | System |
| Leave Application Outcome | Value change on workflow_state | Document owner | System |

#### 2.2.5 Email Templates
- **Leave Approval Notification**: Sent to approver with employee name, leave type, dates, reason
- **Leave Status Notification**: Sent to employee with application status and workflow state

#### 2.2.6 Escalation
- After `escalation_days` (default: 2) of inactivity, reminder email sent to leave_approver or fallback_email
- Controlled by `enable_escalation_reminders` setting

#### 2.2.7 Custom Fields on Leave Application

| Field | Type | Description |
|-------|------|-------------|
| custom_from_time | Time | Start time for half-day leaves |
| custom_to_time | Time | End time for half-day leaves |

---

### 2.3 Attendance Request (Correction)

**Module:** `server_script/attendance_request_validation.py`, `public/js/attendance_request.js`
**DocType:** Attendance Request (extended)

#### 2.3.1 Business Rules

| # | Rule | Configurable | Setting |
|---|------|-------------|---------|
| 1 | From Date cannot be after To Date | No | - |
| 2 | Only past dates allowed (no today or future) | No | Hardcoded |
| 3 | Restricted to current month only | Yes | `restrict_to_current_month` (default: 1) |
| 4 | Maximum requests per month per employee | Yes | `max_attendance_requests_per_month` (default: 5) |
| 5 | Locked attendance cannot be corrected | No | Checks `custom_locked` field |
| 6 | Submitted Attendance must exist for each date | No | - |
| 7 | Attendance status must be in allowed list | Yes | `allowed_attendance_statuses` (default: Present, Work From Home, Half Day) |
| 8 | Approver auto-assigned from employee's Shift Request Approver | No | - |
| 9 | Non-TL employees must have approver assigned | No | - |

#### 2.3.2 Approval Workflow

**Workflow Name:** "Attendence Request Workflow"

Same 2-tier structure as Leave Application:
- Draft → Pending (via TL) OR Draft → Pending HR Approve (if employee is TL)
- Pending → Rejected by TL OR Pending → Pending HR Approve (Verify&Forward)
- Pending HR Approve → Approved by HR

**Transition Conditions:**
- TL actions: `frappe.session.user == doc.approver`
- HR approval: HR Manager role, self-approval allowed

#### 2.3.3 Notifications
- Pending approval notifications to TL/HR
- Outcome notifications to document owner

#### 2.3.4 UI Behavior
- Auto-fills employee, employee_name, company from logged-in user
- Fields made read-only after auto-fill

---

### 2.4 Meal Ordering & QR System

**Modules:** `api.py`, `scheduled_tasks.py`, `doctype/food_qr/`, `doctype/food_count/`, `doctype/food_menu_item/`, `doctype/food_report/`

#### 2.4.1 DocTypes

**Food Menu Item** - Weekly menu definition:

| Field | Type | Description |
|-------|------|-------------|
| day | Select | Monday through Sunday (required) |
| available | Check | Whether menu is active (default: 1) |
| breakfast_item | Data | Breakfast dish name (required) |
| breakfast_description | Text | Description |
| lunch_item | Data | Lunch dish name |
| lunch_description | Text | Description |
| dinner_item | Data | Dinner dish name |
| dinner_description | Text | Description |

**Food Count** - Employee meal order per day:

| Field | Type | Description |
|-------|------|-------------|
| user | Link to User | Auto-set to current user |
| order_date | Date | Auto-set to tomorrow for new records |
| breakfast_selected | Check | Employee orders breakfast |
| breakfast | Data | Menu item display (read-only) |
| breakfast_status | Select | Not Ordered / Pending / Consumed / Not Consumed / Cancelled |
| lunch_selected | Check | Employee orders lunch |
| lunch | Data | Menu item display (read-only) |
| lunch_status | Select | Same options as breakfast |
| dinner_selected | Check | Employee orders dinner |
| dinner | Data | Menu item display (read-only) |
| dinner_status | Select | Same options as breakfast |

**Food QR** - Generated QR records per meal slot:

| Field | Type | Description |
|-------|------|-------------|
| date | Date | Meal date (required, indexed) |
| day | Data | Day of week (auto-calculated) |
| food_type | Select | Breakfast / Lunch / Dinner |
| food_item | Data | Menu item name |
| status | Select | Pending / Scheduled / Active / Consumed / Cancelled / Closed |
| vendor | Link to User | Assigned vendor |
| serving_time | Time | Start of serving window |
| window_start | Time | Window open time |
| window_end | Time | Window close time |
| food_put_count | Int | Live count of employee orders |
| consumed_count | Int | Count of meals collected via QR scan |
| qr_data | Data | Payload: "FQR\|{date}\|{food_type}\|{unique_id}" |
| qr_image_url | Data | External QR image URL |
| qr_display | HTML | Visual QR preview |

**Food Report** - Meal consumption reporting:

| Field | Type | Description |
|-------|------|-------------|
| user | Link to User | Required |
| report_date | Date | Required |
| breakfast_consumed | Check | Default: 1 |
| breakfast_remarks | Small Text | Comments |
| lunch_consumed/remarks | Same pattern | |
| dinner_consumed/remarks | Same pattern | |

#### 2.4.2 Meal System Business Rules

| # | Rule | Configurable | Setting |
|---|------|-------------|---------|
| 1 | Entire meal system can be disabled | Yes | `enable_meal_system` (default: 1) |
| 2 | Meal windows define when QR is active | Yes | `meal_breakfast_open/close`, `meal_lunch_open/close`, `meal_dinner_open/close` |
| 3 | QR scan only during active window | No | Validated against window times |
| 4 | Only ordered meals can be collected | No | Checks breakfast/lunch/dinner_selected |
| 5 | Each meal can only be collected once per person | No | Checks status != Consumed |
| 6 | Cancelled orders cannot be collected | No | - |
| 7 | Meal cancellation before window opens | Yes | `enable_meal_cancellation` (default: 1) |
| 8 | Pre-ordering capability | Yes | `enable_meal_pre_order` (default: 0) |
| 9 | Dietary preference tracking | Yes | `enable_dietary_preference` (default: 1) |

#### 2.4.3 Meal System Lifecycle

```
Daily 00:00   ──► create_food_qr_records() generates QR for today (status: Scheduled)
                  food_put_count set from current Food Count orders

09:00 AM      ──► activate_breakfast_qr() → status: Active
                  Employees scan QR to collect breakfast
11:01 AM      ──► mark_breakfast_not_consumed() → remaining Pending → Not Consumed
                  close_food_qr() → status: Closed

12:30 PM      ──► activate_lunch_qr() → status: Active
15:01 PM      ──► mark_lunch_not_consumed() → close

19:00 PM      ──► activate_dinner_qr() → status: Active
22:01 PM      ──► mark_dinner_not_consumed() → close
```

#### 2.4.4 QR Scan Flow (API: `scan_food_qr`)

1. Parse QR data (format: `FQR|date|food_type|unique_id` or direct docname)
2. Validate QR status is "Active"
3. Validate current time is within meal window
4. Find employee's Food Count for today
5. Validate meal was ordered (selected checkbox = 1)
6. Validate meal not already consumed
7. Update Food Count status to "Consumed"
8. Increment QR consumed_count
9. Return success with meal info and count

#### 2.4.5 Meal Cancellation Flow (API: `cancel_meal_order`)

1. Check `enable_meal_cancellation` is on
2. Validate current user owns the order
3. QR status must be "Pending" or "Scheduled" (before window opens)
4. Set selected checkbox to 0, status to "Cancelled"
5. Decrement food_put_count on Food QR

#### 2.4.6 Food Count Sync (Hook: `update_food_qr_count`)

Triggered on Food Count insert/update:
- Recalculates order count per meal type
- Updates linked Food QR food_put_count
- Sets meal status to "Pending" (if selected) or "Not Ordered" (if unselected)
- Preserves "Consumed" status (no override)

---

### 2.5 Interview Scheduling

**Module:** `server_script/interview_round.py`, `public/js/interview.js`
**DocType:** Interview (extended)

#### 2.5.1 Business Rules

| # | Rule | Configurable | Setting |
|---|------|-------------|---------|
| 1 | Administrator and System Manager bypass all validations | No | Hardcoded |
| 2 | interview_round, job_applicant, scheduled_on required | No | - |
| 3 | from_time and to_time required | No | - |
| 4 | custom_interview_type required | No | - |
| 5 | Interview Round must belong to selected Interview Type | No | - |
| 6 | Cannot schedule for past dates | No | - |
| 7 | If today: from_time and to_time must be future | No | - |
| 8 | to_time must be after from_time | No | - |
| 9 | One interview per round per applicant (no duplicates) | No | - |
| 10 | Rounds must be completed sequentially | No | Based on round_order |
| 11 | Previous round must be "Cleared" to schedule next | No | - |

#### 2.5.2 Round Order Enforcement
- Each Interview Round has a `round_order` field
- Round 1: no prerequisites
- Round N (N>1): all rounds 1..N-1 must have scheduled interview with status "Cleared"
- If previous round is "Rejected": blocks scheduling entirely
- If previous round is "Pending": blocks until resolved

#### 2.5.3 UI Behavior
- Interview Type must be selected before Interview Round
- Interview Round dropdown filtered by selected Interview Type
- Auto-validates round belongs to type on selection change

#### 2.5.4 Custom Fields on Interview

| Field | Type | Description |
|-------|------|-------------|
| custom_interview_type | Link to Interview Type | Mandatory, placed at index 1 |

---

### 2.6 Employee Separation (Offboarding)

**Module:** `server_script/employee_separation_validation.py`, `public/js/employee_separation.js`
**DocType:** Employee Separation (extended)

#### 2.6.1 Approval Workflow

**Workflow Name:** "Employee Separation Workflow"

```
Draft (Employee) → Pending HR Review (HR Manager) → Pending Approval (HR Manager)
                                                          │
                                               ┌──────────┴──────────┐
                                               ▼                     ▼
                                         Approved (Head)       Rejected (Head)
                                         [submitted]                │
                                                              Re-Apply → Draft
```

#### 2.6.2 Automated Actions on Approval
When workflow_state changes to "Approved":
1. Employee record status set to "Left"
2. Relieving date set to current date (today)
3. Linked user account disabled (enabled=0)
4. Info comment added to separation document

#### 2.6.3 Custom Fields

| Field | Type | Description |
|-------|------|-------------|
| custom_reason | Small Text | Reason for separation (mandatory, in list view, read-only) |

#### 2.6.4 UI Behavior
- Auto-fills employee data for pure Employee role users
- Pre-fills: employee, employee_name, department, designation, company
- Employee field locked after fill

---

### 2.7 Expense Claim Management

**Module:** `public/js/expense_claim.js`
**DocType:** Expense Claim (extended)

#### 2.7.1 Approval Workflow

**Workflow Name:** "Expense Claim Workflow"

```
Pending Approval (Employee) ──► Approved (HR Manager, submitted)
                            └──► Rejected (HR Manager)
                                      │
                                 Re-Apply → Pending Approval
```

Simple 1-tier approval by HR Manager with re-apply option.

#### 2.7.2 Notifications
- Routing: System notification to HR Manager when submitted
- Outcome: Email notification to employee when approved/rejected

#### 2.7.3 UI Behavior
- Auto-fills employee, employee_name, company from logged-in user
- All auto-filled fields made read-only

---

### 2.8 Payroll Management

**Module:** `public/js/payroll_entry.js`, `api.py`
**DocType:** Payroll Entry (extended)

#### 2.8.1 Approval Workflow

**Workflow Name:** "Payroll Entry Approval"

```
Draft (HR Manager) ──► Pending Approval (HR Manager)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Approved (Head)     Rejected (Head)
              [submitted]              │
                                 Re-generate → Pending Approval
```

#### 2.8.2 Payroll Readiness Check (API: `check_payroll_readiness`)

Returns checklist for date range:
- Count of pending leave approvals (workflow_state: "Pending HR Approve")
- Count of pending attendance corrections (workflow_state: "Pending HR Approve")
- Count of unsynced Employee Checkins (no linked Attendance)
- Overall readiness boolean

UI: "Check Payroll Readiness" button on draft Payroll Entry, displays color-coded table.

#### 2.8.3 Attendance Lock After Payroll
- Daily scheduled task: `lock_attendance_for_processed_payroll()`
- For each submitted Payroll Entry: sets `custom_locked=1` on Attendance in date range
- Prevents subsequent Attendance Requests for locked periods
- Controlled by `enable_payroll_period_lock` setting

---

### 2.9 Job Requisition

**DocType:** Job Requisition (standard, with custom workflow)

#### 2.9.1 Approval Workflow

**Workflow Name:** "Job Requisition workflow"

```
Draft (Projects Manager) → Pending HR Review (HR Manager) → Pending Head Approval (Head)
                                                                    │
                                                          ┌────────┴────────┐
                                                          ▼                 ▼
                                                    Approved (HR Manager)  Rejected (HR Manager)
                                                    [submitted]
                                                    status: "Open & Approved"
```

---

### 2.10 Dashboards

#### 2.10.1 Employee Dashboard

**Number Cards:**
- Total Present (This Month)
- Total Absent (This Month)
- Attendance Request Pending
- Leave Request Pending

**Charts:**
- Attendance Count Monthly (Full Width)

#### 2.10.2 CEO Dashboard

**Number Cards:**
- Total Outgoing Salary (Last Month)
- Total Employees
- Employee Exits (This Year)
- New Hires (This Year)
- Expense Claim Request Pending
- Leave Request Pending
- Attendance Request Pending

**Charts:**
- Hiring vs Attrition Count (Full Width)
- Outgoing Salary (Full Width)
- Monthly Leave Report (Full Width)
- Employees by Age (Half Width)
- Department Wise Employee Count (Half Width)
- Employees by Branch (Half Width)
- Designation Wise Employee Count (Half Width)

---

### 2.11 Notification System

#### 2.11.1 Real-Time Notification Sidebar
- Fixed right sidebar (280px) showing unread notifications
- Auto-refreshes every 60 seconds
- Listens to real-time events for instant updates
- "Mark all as read" functionality
- Click navigates to source document

#### 2.11.2 Toast Notifications
- Pop-up toasts for new notifications (3-second auto-dismiss)
- LocalStorage deduplication prevents duplicate popups
- Fetches latest 15 on load, 5 on intervals (8 seconds)

#### 2.11.3 Escalation System
- Pending leave/attendance approvals escalated after N days
- Sends email to assigned approver or fallback email
- For attendance in "Pending HR Approve": emails all HR Manager users
- Controlled by `enable_escalation_reminders` and `escalation_days` settings

---

### 2.12 Workspaces

| Workspace | Roles | Key Shortcuts/Links |
|-----------|-------|-------------------|
| Employee Workspace | Employee, Administrator | My Profile, CheckIn/CheckOut, Attendance, Attendance Request, Leave Application, Expense Claim, Salary Slip, Employee Relieving Request |
| HR Workspace | HR Manager | Employee management, Leave, Attendance, Payroll, Recruitment |
| TL Workspace | Team Leader | Team approvals, attendance reviews |
| CEO Workspace | CEO, Administrator | Payroll, Employee Overview, Recruitment, Leave & Attendance, Offboarding |

---

## 3. Non-Functional Requirements

### 3.1 Centralized Configuration
All business rules are managed through **Finstein HRMS Settings** (single-instance DocType):

| Section | Settings |
|---------|----------|
| Leave Policy | max_continuous_leave_days, leave_submission_cutoff_time, half_day_cutoff_time, allow_past_date_leave, enable_leave_balance_check, enable_leave_withdrawal |
| Attendance Policy | max_attendance_requests_per_month, allowed_attendance_statuses, restrict_to_current_month, enable_attendance_lock_after_payroll |
| Check-In Policy | min_checkin_hours, shift_start_time, shift_end_time, enable_late_entry_tagging, enable_early_exit_tagging, enable_overtime_tracking, enable_force_checkout |
| Approval & Escalation | escalation_days, escalation_email, enable_escalation_reminders, enable_auto_rejection, auto_reject_days |
| Meal System | enable_meal_system, meal windows (6 time fields), enable_meal_pre_order, enable_meal_cancellation, enable_dietary_preference |
| Notifications | enable_email_notifications, enable_inapp_notifications, notification_sender_email |
| Payroll | enable_payroll_readiness_check, enable_payroll_period_lock, auto_email_salary_slips, payroll_notification_email |

### 3.2 Scheduled Tasks

| Schedule | Task | Description |
|----------|------|-------------|
| Daily | create_food_qr_records | Generate Food QR records for today |
| Daily | escalate_pending_approvals | Send reminder emails for stale approvals |
| Daily | lock_attendance_for_processed_payroll | Lock attendance for payroll periods |
| 09:00 | activate_breakfast_qr | Set breakfast QR to Active |
| 11:01 | mark_breakfast_not_consumed | Close breakfast window |
| 12:30 | activate_lunch_qr | Set lunch QR to Active |
| 15:01 | mark_lunch_not_consumed | Close lunch window |
| 19:00 | activate_dinner_qr | Set dinner QR to Active |
| 22:01 | mark_dinner_not_consumed | Close dinner window |

### 3.3 API Endpoints

| Endpoint | Auth | Method | Description |
|----------|------|--------|-------------|
| `scan_food_qr(qr_data)` | allow_guest=False | POST | Validate QR scan, mark meal consumed |
| `get_todays_food_qr()` | allow_guest=False | GET | List today's meal QR slots |
| `get_my_order_status()` | allow_guest=False | GET | Current user's meal statuses |
| `withdraw_leave_application(docname)` | whitelist | POST | Withdraw pending leave |
| `is_employee_team_leader(employee)` | whitelist | GET | Check if employee is TL |
| `cancel_meal_order(qr_name)` | whitelist | POST | Cancel meal before window |
| `check_payroll_readiness(start_date, end_date)` | whitelist | GET | Payroll readiness checklist |
| `get_menu_for_date(order_date)` | whitelist | GET | Menu items for a date |
| `generate_qr(name, force_regenerate)` | whitelist | POST | Generate/regenerate QR code |

### 3.4 Custom Fields on Standard DocTypes

| DocType | Custom Fields |
|---------|--------------|
| Employee | custom_dietary_preference (Select: Vegetarian/Non-Vegetarian/Vegan/Jain) |
| Employee Checkin | checkout_time, log_type_out, break_start, break_end, break_hours, working_hours, attendance_status, checkout_type |
| Leave Application | custom_from_time, custom_to_time |
| Attendance | custom_late_entry, custom_early_exit, custom_overtime_hours, custom_locked |
| Attendance Request | workflow_state |
| Employee Separation | custom_reason, workflow_state |
| Expense Claim | workflow_state |
| Interview | custom_interview_type |
| Food Count | breakfast_status, lunch_status, dinner_status |

### 3.5 Document Permissions

| Role | DocTypes with Full Access |
|------|--------------------------|
| HR Manager | Salary Component, Employee Separation, Employee Separation Template, Food Menu Item, Workflow, Company (Read/Write) |
| Head | Employee Separation, Employee, Leave Allocation, Leave Application, Expense Claim, Attendance, Attendance Request, Employee Advance, Employee Checkin, Employee Onboarding |
| Employee | Resignation Request (Create/Write), Employee Separation (Create/Read/Write/Submit) |
| Food Provider | Food Menu Item (CRUD) |

### 3.6 Fixtures
The app exports and maintains these fixtures:
- Custom DocPerm (all custom permissions)
- Active Workflows (6 workflows)
- Notifications (for 6 document types)
- Workspaces (CEO, Employee, HR, TL)
- Finstein HRMS Settings (singleton config)

---

## 4. Issues & Gaps Identified

### 4.1 Critical Security Issues

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 1 | Missing `allow_guest=False` on 4 API endpoints | api.py:221,246,264,334 | Unauthenticated users may access leave withdrawal, meal cancellation, payroll data | Add `allow_guest=False` |
| 2 | Hardcoded demo password `Demo@123` | demo_data.py:5 | Known credentials if demo data loaded in non-dev environment | Generate random or use env var |
| 3 | No role check on `check_payroll_readiness()` | api.py:334-379 | Any authenticated user sees org-wide payroll metrics | Add `frappe.only_for()` |
| 4 | Low-entropy QR unique_id (40 bits) | scheduled_tasks.py:75 | QR codes potentially brute-forceable | Use full UUID |

### 4.2 High Priority Issues

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 5 | `ignore_permissions=True` in API handlers | api.py:238,318 | Bypasses permission system in user-facing endpoints | Remove or add explicit role checks |
| 6 | Race condition in QR scan (non-atomic increment) | api.py:154-157 | Concurrent scans lose consumed_count | Use SQL atomic increment |
| 7 | Race condition in meal cancellation | api.py:320-326 | Concurrent cancellations corrupt food_put_count | Use SQL atomic decrement |
| 8 | External QR image service dependency | scheduled_tasks.py:77 | Service outage breaks QR display; leaks data | Use local `qrcode` library |
| 9 | Excessive `frappe.db.commit()` in API handlers | api.py:157,239,328 | Partial commits on error; Frappe auto-commits | Remove manual commits |

### 4.3 Medium Priority Issues

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 10 | Duplicate lock check in attendance request validation | attendance_request_validation.py:33,83-106 | Unnecessary DB queries |
| 11 | Leave withdrawal doesn't clear approval fields | api.py:237 | Potential data inconsistency |
| 12 | Settings loaded repeatedly without caching | scheduled_tasks.py (multiple) | Unnecessary DB reads |
| 13 | Notification template is placeholder | leave_request.html | "Add your message here" sent to users |
| 14 | Overly permissive linting rules | .eslintrc, pyproject.toml | Hides dead code and import issues |
| 15 | Broad exception catching | api.py:23, scheduled_tasks.py:18 | Silently swallows programming errors |
| 16 | No test coverage for API endpoints | tests/ | Security-sensitive code untested |
| 17 | lock_attendance re-locks all historical payrolls daily | scheduled_tasks.py:439-458 | Unnecessary DB updates |

### 4.4 Low Priority Issues

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 18 | HTML built via f-string interpolation | scheduled_tasks.py:96-105 | Potential XSS (mitigated by Frappe) |
| 19 | Deeply nested callbacks in frontend JS | employee_checkin_client.js | Code maintainability |
| 20 | Admin/HR blocked from all checkin operations | checkin_validation.py:145-163 | Cannot make legitimate corrections |

---

## 5. Summary Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| Security | 5/10 | Missing auth on 4 endpoints, hardcoded password, race conditions |
| Code Quality | 7/10 | Clean structure, good separation, but permissive linting |
| Test Coverage | 4/10 | Validations tested; API endpoints and integration untested |
| Architecture | 8/10 | Good Frappe patterns, configurable settings, clean modules |
| Business Logic | 8/10 | Comprehensive validations, proper workflows, configurable policies |
| Frontend | 6/10 | Functional but older patterns, some forms minimal |
| DevOps/CI | 7/10 | GitHub Actions + security scanning; no Docker/staging |
| Documentation | 3/10 | Minimal README, placeholder templates, no API docs |

**Overall: 6/10** - Solid business logic and architecture with security gaps needing immediate attention.

---

## 6. Auto-Populated Fields Reference

This section documents every field in the system that is automatically set by server-side logic, client-side JavaScript, scheduled tasks, or API handlers — without direct user input.

### 6.1 Employee Checkin

#### Client-Side Auto-Population (employee_checkin_client.js)

| Field | Trigger | Value Set | Source |
|-------|---------|-----------|--------|
| `employee` | Form load (new doc) | Current user's linked Employee ID | `frappe.db.get_value("Employee", {user_id})` |
| `employee_name` | Form load (new doc) | Employee's full name | Fetched with employee lookup |
| `time` | Click "Check In" button | `frappe.datetime.now_datetime()` | Client-side current timestamp |
| `log_type` | Click "Check In" button | `"IN"` | Hardcoded |
| `checkout_time` | Click "Check Out" or "Force Checkout" button | `frappe.datetime.now_datetime()` | Client-side current timestamp |
| `log_type_out` | Click "Check Out" / "Force Checkout" | `"OUT"` or `"FORCE OUT"` | Based on checkout method |
| `checkout_type` | Click "Check Out" / "Force Checkout" | `"Normal"` or `"Force"` | Based on checkout method |
| `break_start` | Click "Permission Checkout" button | `frappe.datetime.now_datetime()` | Client-side current timestamp |
| `break_end` | Click "Permission Check-In" button | `frappe.datetime.now_datetime()` | Client-side current timestamp |
| `break_hours` | Click "Permission Check-In" button | Accumulated break duration | `current_break_hours + (break_end - break_start)` in hours |
| `working_hours` | Click "Check Out" / "Force Checkout" | Elapsed time minus breaks | `(checkout_time - time) - break_hours` (client pre-calculation) |
| `attendance_status` | Click "Check Out" / "Force Checkout" | `"Present"` / `"Half Day"` / `"Absent"` | Based on working_hours vs min_checkin_hours (client pre-calculation) |

#### Server-Side Auto-Population (checkin_validation.py — before_save)

| Field | Function | Value Set | Condition |
|-------|----------|-----------|-----------|
| `working_hours` | `_calc_hours()` | `round(max((checkout_time - time) - break_hours, 0), 2)` | Both time and checkout_time are set |
| `attendance_status` | `_set_status()` | `"Present"` if worked >= min_hours, `"Half Day"` if >= min_hours/2, else `"Absent"` | checkout_time is set |

#### Server-Side Cross-DocType Effects (checkin_validation.py — after_insert/on_update)

| Target DocType | Target Field | Function | Value Set | Condition |
|----------------|-------------|----------|-----------|-----------|
| **Attendance** | `status` | `sync_attendance_from_checkin()` | Copied from Employee Checkin.attendance_status (default: `"Absent"`) | Employee, time, and checkout_time all present |
| **Attendance** | `docstatus` | `sync_attendance_from_checkin()` | `1` (submitted) | New attendance auto-submitted; existing draft auto-submitted |
| **Attendance** | `custom_late_entry` | `tag_attendance_anomalies()` | `1` | `enable_late_entry_tagging` ON and checkin_time > shift_start_time |
| **Attendance** | `custom_early_exit` | `tag_attendance_anomalies()` | `1` | `enable_early_exit_tagging` ON and checkout_time < shift_end_time |
| **Attendance** | `custom_overtime_hours` | `calculate_and_store_overtime()` | `round(worked_hours - min_checkin_hours, 2)` | `enable_overtime_tracking` ON and worked_hours > min_checkin_hours |

---

### 6.2 Leave Application

#### Client-Side Auto-Population (leave_application.js)

| Field | Trigger | Value Set | Condition |
|-------|---------|-----------|-----------|
| `custom_from_time` | `half_day` checkbox unchecked | `null` (cleared) | User toggles half_day off |
| `custom_to_time` | `half_day` checkbox unchecked | `null` (cleared) | User toggles half_day off |
| `leave_approver` | Form load / employee change | `""` (cleared) | Employee is a Team Leader (skips TL approval tier) |
| `leave_approver_name` | Form load / employee change | `""` (cleared) | Employee is a Team Leader |

#### API Auto-Population (api.py — withdraw_leave_application)

| Field | Trigger | Value Set | Condition |
|-------|---------|-----------|-----------|
| `workflow_state` | Employee calls withdraw API | `"Draft"` | Current state is "Pending" or "Pending HR Approve" and owner == session.user |

---

### 6.3 Attendance Request

#### Client-Side Auto-Population (attendance_request.js)

| Field | Trigger | Value Set | Source |
|-------|---------|-----------|--------|
| `employee` | Form load (new doc) | Current user's linked Employee ID | `frappe.db.get_value("Employee", {user_id})` |
| `company` | Form load (new doc) | Employee's company | Fetched with employee lookup |

#### Server-Side Auto-Population (attendance_request_validation.py — validate)

| Field | Function | Value Set | Source |
|-------|----------|-----------|--------|
| `approver` | `_set_attendance_request_approver()` | Employee's `shift_request_approver` field | `frappe.db.get_value("Employee", doc.employee, "shift_request_approver")` |

---

### 6.4 Employee Separation

#### Client-Side Auto-Population (employee_separation.js)

| Field | Trigger | Value Set | Condition |
|-------|---------|-----------|-----------|
| `employee` | Form load (new doc) | Current user's linked Employee ID | User has only Employee role (no HR Manager, System Manager, Head) |
| `employee_name` | Form load (new doc) | Employee's full name | Same condition |
| `department` | Form load (new doc) | Employee's department | Same condition |
| `designation` | Form load (new doc) | Employee's designation | Same condition |
| `company` | Form load (new doc) | Employee's company | Same condition |

#### Server-Side Cross-DocType Effects (employee_separation_validation.py — on_update)

| Target DocType | Target Field | Value Set | Condition |
|----------------|-------------|-----------|-----------|
| **Employee** | `status` | `"Left"` | Employee Separation workflow_state == "Approved" |
| **Employee** | `relieving_date` | `date.today()` (YYYY-MM-DD) | Employee Separation workflow_state == "Approved" |
| **User** | `enabled` | `0` (disabled) | Employee Separation workflow_state == "Approved" and employee has linked user_id |
| **Comment** | (new record) | Info comment documenting the separation | Employee Separation workflow_state == "Approved" |

---

### 6.5 Expense Claim

#### Client-Side Auto-Population (expense_claim.js)

| Field | Trigger | Value Set | Source |
|-------|---------|-----------|--------|
| `employee` | Form load (new doc) | Current user's linked Employee ID | `frappe.db.get_value("Employee", {user_id})` |
| `employee_name` | Form load (new doc) | Employee's full name | Fetched with employee lookup |
| `company` | Form load (new doc) | Employee's company | Fetched with employee lookup |

---

### 6.6 Food QR

#### Scheduled Task Auto-Population (scheduled_tasks.py — create_food_qr_records, daily)

All Food QR fields are auto-generated. No user input is required.

| Field | Value Source | Description |
|-------|-------------|-------------|
| `date` | `nowdate()` | Today's date |
| `day` | `DAY_NAMES[getdate(date).weekday()]` | Computed day name (Monday-Sunday) |
| `food_type` | Food Menu Item iteration | `"Breakfast"`, `"Lunch"`, or `"Dinner"` |
| `food_item` | Food Menu Item for this day | Menu item name (e.g., "Idli & Sambar") |
| `serving_time` | Finstein HRMS Settings | Meal window open time |
| `window_start` | Finstein HRMS Settings | `meal_breakfast_open` / `meal_lunch_open` / `meal_dinner_open` |
| `window_end` | Finstein HRMS Settings | `meal_breakfast_close` / `meal_lunch_close` / `meal_dinner_close` |
| `status` | Hardcoded initial | `"Scheduled"` on creation |
| `food_put_count` | `_get_order_count()` | Count of Food Count records where `{meal}_selected = 1` for this date |
| `consumed_count` | Hardcoded initial | `0` on creation |
| `qr_data` | Generated | `"FQR|{date}|{food_type}|{uuid.hex[:10].upper()}"` |
| `qr_image_url` | Generated | `"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_data}"` |
| `qr_display` | Generated | HTML block with QR image, meal name, date, and window times |

#### Lifecycle Status Changes (scheduled tasks + API)

| Field | New Value | Trigger | Function |
|-------|-----------|---------|----------|
| `status` | `"Active"` | Cron: 09:00/12:30/19:00 | `_activate_food_qr()` |
| `status` | `"Closed"` | Cron: 11:01/15:01/22:01 | `_close_food_qr()` |
| `consumed_count` | `+1` increment | Employee scans QR | `scan_food_qr()` in api.py |
| `food_put_count` | Recalculated count | Food Count insert/update | `update_food_qr_count()` in scheduled_tasks.py |
| `food_put_count` | `max(current - 1, 0)` | Employee cancels meal | `cancel_meal_order()` in api.py |

---

### 6.7 Food Count

#### Hook Auto-Population (scheduled_tasks.py — update_food_qr_count, on Food Count insert/update)

| Field | Value Set | Condition |
|-------|-----------|-----------|
| `breakfast_status` | `"Pending"` | `breakfast_selected = 1` and current status != `"Consumed"` |
| `breakfast_status` | `"Not Ordered"` | `breakfast_selected = 0` and current status != `"Consumed"` |
| `lunch_status` | `"Pending"` | `lunch_selected = 1` and current status != `"Consumed"` |
| `lunch_status` | `"Not Ordered"` | `lunch_selected = 0` and current status != `"Consumed"` |
| `dinner_status` | `"Pending"` | `dinner_selected = 1` and current status != `"Consumed"` |
| `dinner_status` | `"Not Ordered"` | `dinner_selected = 0` and current status != `"Consumed"` |

#### Scheduled Task Auto-Population (mark_*_not_consumed, cron)

| Field | Value Set | Trigger |
|-------|-----------|---------|
| `breakfast_status` | `"Not Consumed"` | 11:01 cron — for records where `breakfast_selected=1` and `breakfast_status="Pending"` |
| `lunch_status` | `"Not Consumed"` | 15:01 cron — for records where `lunch_selected=1` and `lunch_status="Pending"` |
| `dinner_status` | `"Not Consumed"` | 22:01 cron — for records where `dinner_selected=1` and `dinner_status="Pending"` |

#### API Auto-Population (api.py — scan_food_qr)

| Field | Value Set | Trigger |
|-------|-----------|---------|
| `breakfast_status` / `lunch_status` / `dinner_status` | `"Consumed"` | Employee scans QR for the corresponding meal type |

#### API Auto-Population (api.py — cancel_meal_order)

| Field | Value Set | Trigger |
|-------|-----------|---------|
| `breakfast_selected` / `lunch_selected` / `dinner_selected` | `0` | Employee cancels the corresponding meal order |
| `breakfast_status` / `lunch_status` / `dinner_status` | `"Cancelled"` | Employee cancels the corresponding meal order |

---

### 6.8 Attendance (Payroll Lock)

#### Scheduled Task Auto-Population (scheduled_tasks.py — lock_attendance_for_processed_payroll, daily)

| Field | Value Set | Condition |
|-------|-----------|-----------|
| `custom_locked` | `1` | `enable_payroll_period_lock` ON, attendance_date falls within a submitted Payroll Entry's date range, docstatus=1, not already locked |

---

### 6.9 Auto-Populated Fields Summary

| DocType | Total Auto Fields | Client-Side | Server-Side (validate) | Server-Side (post-save) | Scheduled Tasks | API |
|---------|-------------------|-------------|----------------------|------------------------|-----------------|-----|
| Employee Checkin | 14 | 12 | 2 | — | — | — |
| Attendance | 5 | — | — | 4 (from checkin sync) | 1 (payroll lock) | — |
| Leave Application | 5 | 4 | — | — | — | 1 |
| Attendance Request | 3 | 2 | 1 | — | — | — |
| Employee Separation | 5 | 5 | — | — | — | — |
| Employee (cross-doctype) | 2 | — | — | 2 (from separation) | — | — |
| User (cross-doctype) | 1 | — | — | 1 (from separation) | — | — |
| Expense Claim | 3 | 3 | — | — | — | — |
| Food QR | 13+ | — | — | — | 13 (creation) + 4 (lifecycle) | 2 |
| Food Count | 9 | — | — | 6 (from hook) | 3 (window close) | 6 |
| **TOTAL** | **60+** | **26** | **3** | **13** | **21+** | **9** |

#### Auto-Population Trigger Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AUTO-POPULATION TRIGGERS                            │
├──────────────────────┬──────────────────────────────────────────────────┤
│ CLIENT-SIDE (JS)     │ Form onload/refresh (26 fields)                 │
│                      │ Button clicks: Check In, Check Out, Break       │
│                      │ Checkbox toggles: half_day                      │
├──────────────────────┼──────────────────────────────────────────────────┤
│ SERVER validate      │ Employee Checkin before_save (2 fields)         │
│                      │ Attendance Request validate (1 field)           │
├──────────────────────┼──────────────────────────────────────────────────┤
│ SERVER post-save     │ Employee Checkin after_insert/on_update →       │
│                      │   creates/updates Attendance (4 fields)         │
│                      │ Employee Separation on_update →                 │
│                      │   updates Employee + User (3 fields)            │
│                      │ Food Count after_insert/on_update →             │
│                      │   updates Food Count statuses + Food QR (6+)   │
├──────────────────────┼──────────────────────────────────────────────────┤
│ SCHEDULED TASKS      │ Daily: Food QR creation (13 fields per record)  │
│                      │ Cron: QR activation (status → Active)           │
│                      │ Cron: Window close (status → Closed/Not Consumed│
│                      │ Daily: Payroll lock (custom_locked → 1)         │
├──────────────────────┼──────────────────────────────────────────────────┤
│ API ENDPOINTS        │ scan_food_qr: Food Count status + QR count      │
│                      │ cancel_meal_order: Food Count + QR put_count    │
│                      │ withdraw_leave_application: workflow_state       │
└──────────────────────┴──────────────────────────────────────────────────┘
```
