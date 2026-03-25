# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finstein HRMS is a custom Frappe/ERPNext app that extends HR Module (hrms) with company-specific business rules, validations, and a meal/food QR management system. It runs on Frappe Framework v15 with Python 3.10+.

## Common Commands

```bash
# Install the app
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app finstein_hrms

# Run all tests
bench --site <site-name> run-tests --app finstein_hrms

# Run a single test file
bench --site <site-name> run-tests --module tests.test_leave_validation

# Migrate after doctype/schema changes
bench --site <site-name> migrate

# Lint
ruff check finstein_hrms/
ruff format finstein_hrms/

# Pre-commit (ruff, eslint, prettier, pyupgrade)
pre-commit run --all-files
```

## Architecture

### Frappe App Structure

The app follows the standard Frappe app layout with a **nested module directory**: `finstein_hrms/finstein_hrms/` contains the "Finstein HRMS" module with its doctypes and notifications.

### Central Settings Pattern

All configurable business rules are stored in a **single Settings doctype** (`Finstein HRMS Settings`), a Frappe Single DocType. Every validation and scheduled task imports the same helper:

```python
from finstein_hrms.finstein_hrms.doctype.finstein_hrms_settings.finstein_hrms_settings import get_settings
```

Feature flags on this settings doc control: meal system, leave balance checks, force checkout, escalation reminders, overtime tracking, late/early tagging, payroll period locking, attendance request limits, and more.

### Hook-Driven Validation Layer

The app does not override standard ERPNext controllers. Instead, `hooks.py` registers `doc_events` that route to validation modules under `finstein_hrms/server_script/`:

| ERPNext DocType | Hook | Validation Module |
|---|---|---|
| Leave Application | validate | `server_script/leave_validation.py` |
| Employee Checkin | before_save, after_insert, on_update | `server_script/checkin_validation.py` |
| Attendance Request | validate | `server_script/attendance_request_validation.py` |
| Interview | validate | `server_script/interview_round.py` |
| Employee Separation | on_update | `server_script/employee_separation_validation.py` |
| Food Count | after_insert, on_update | `scheduled_tasks.py` (update_food_qr_count) |

### Meal / Food QR System

A self-contained meal ordering and QR-based collection system with these custom doctypes:
- **Food Menu Item** — weekly menu (per-day breakfast/lunch/dinner items)
- **Food Count** — per-user daily meal selections and consumption status
- **Food QR** — daily QR codes per meal slot with status lifecycle: Scheduled → Active → Closed
- **Food Report** — reporting doctype

Scheduler events in `hooks.py` manage the QR lifecycle (create daily, activate per window, close after window). The whitelisted API in `api.py` handles QR scanning (`scan_food_qr`), order status, and cancellation.

### Client-Side Extensions

`hooks.py` maps `doctype_js` to override client behavior for standard ERPNext doctypes (Employee Checkin, Leave Application, Attendance Request, etc.) via files in `finstein_hrms/public/js/`.

### Fixtures

The app exports and manages: Custom DocPerm, active Workflows, Notifications (for Leave, Attendance, Expense Claim, Employee Separation, Payroll, Job Requisition), Workspaces (CEO, Employee, HR, TL), and Finstein HRMS Settings.

### Test Conventions

Tests live in the top-level `tests/` directory (not inside the module). They use `FrappeTestCase` with `unittest.mock` to mock `get_settings()` and document objects, avoiding database dependency for unit tests.

## Code Style

- **Indent with tabs**, not spaces (configured in `pyproject.toml` ruff settings)
- Line length: 110 characters
- Quote style: double quotes
- Ruff is the linter/formatter (not black/flake8)
