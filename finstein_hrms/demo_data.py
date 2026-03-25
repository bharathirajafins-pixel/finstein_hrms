import json

import frappe

DEMO_PASSWORD = "Demo@123"
DEFAULT_COMPANY = "Finstein"

DEMO_USERS = [
	{
		"email": "demo.employee@finstein.local",
		"first_name": "Demo",
		"last_name": "Employee",
		"roles": ["Employee"],
		"gender": "Male",
		"date_of_birth": "1998-05-12",
		"date_of_joining": "2026-01-06",
		"dietary_preference": "Vegetarian",
	},
	{
		"email": "demo.hr@finstein.local",
		"first_name": "Demo",
		"last_name": "HR",
		"roles": ["Employee", "HR Manager"],
		"gender": "Female",
		"date_of_birth": "1992-08-18",
		"date_of_joining": "2025-04-01",
		"dietary_preference": "Jain",
	},
	{
		"email": "demo.tl@finstein.local",
		"first_name": "Demo",
		"last_name": "Team Lead",
		"roles": ["Employee", "Team Leader"],
		"gender": "Male",
		"date_of_birth": "1994-11-04",
		"date_of_joining": "2025-02-10",
		"dietary_preference": "Non-Vegetarian",
	},
	{
		"email": "demo.ceo@finstein.local",
		"first_name": "Demo",
		"last_name": "CEO",
		"roles": ["Employee", "Head"],
		"gender": "Female",
		"date_of_birth": "1988-01-23",
		"date_of_joining": "2024-01-01",
		"dietary_preference": "Vegan",
	},
]

DEMO_MENUS = {
	"Monday": {
		"breakfast_item": "Idli & Sambar",
		"breakfast_description": "Soft idli served with sambar and chutney",
		"lunch_item": "Veg Biryani",
		"lunch_description": "Aromatic biryani with raita",
		"dinner_item": "Chapati & Paneer Curry",
		"dinner_description": "Whole wheat chapati with paneer gravy",
	},
	"Tuesday": {
		"breakfast_item": "Poha",
		"breakfast_description": "Light poha with peanuts and lemon",
		"lunch_item": "Rajma Rice",
		"lunch_description": "Kidney beans curry with steamed rice",
		"dinner_item": "Dosa & Chutney",
		"dinner_description": "Crispy dosa with coconut chutney",
	},
	"Wednesday": {
		"breakfast_item": "Upma",
		"breakfast_description": "Rava upma with vegetables",
		"lunch_item": "Lemon Rice",
		"lunch_description": "Tangy lemon rice with papad",
		"dinner_item": "Veg Pulao",
		"dinner_description": "Vegetable pulao with curd",
	},
	"Thursday": {
		"breakfast_item": "Pongal",
		"breakfast_description": "Ven pongal with chutney and sambar",
		"lunch_item": "Sambar Rice",
		"lunch_description": "Rice mixed with fresh sambar",
		"dinner_item": "Parotta & Kurma",
		"dinner_description": "Layered parotta with vegetable kurma",
	},
	"Friday": {
		"breakfast_item": "Aloo Paratha",
		"breakfast_description": "Stuffed paratha with curd",
		"lunch_item": "Tomato Rice",
		"lunch_description": "Tomato rice with chips",
		"dinner_item": "Fried Rice",
		"dinner_description": "Veg fried rice with sauce",
	},
	"Saturday": {
		"breakfast_item": "Poori & Masala",
		"breakfast_description": "Puffy poori served with potato masala",
		"lunch_item": "Curd Rice",
		"lunch_description": "Curd rice with pickle",
		"dinner_item": "Mini Meals",
		"dinner_description": "Rice, curry, poriyal, and dal",
	},
	"Sunday": {
		"breakfast_item": "Masala Dosa",
		"breakfast_description": "Masala dosa with chutney and sambar",
		"lunch_item": "Veg Meals",
		"lunch_description": "South Indian full meals",
		"dinner_item": "Noodles",
		"dinner_description": "Vegetable noodles with sauce",
	},
}


def seed_demo_data(company=None):
	"""
	Create reusable demo Users, Employees, and Food Menu Item records.
	Safe to run multiple times.
	"""
	company_name = _resolve_company(company)

	created = {"users": [], "employees": [], "food_menu_items": []}
	updated = {"users": [], "employees": [], "food_menu_items": []}

	for row in DEMO_USERS:
		user_name, was_created = _ensure_demo_user(row)
		(created if was_created else updated)["users"].append(user_name)

		employee_name, emp_created = _ensure_demo_employee(row, company_name)
		(created if emp_created else updated)["employees"].append(employee_name)

	for day, menu in DEMO_MENUS.items():
		menu_name, was_created = _ensure_food_menu_item(day, menu)
		(created if was_created else updated)["food_menu_items"].append(menu_name)

	frappe.db.commit()

	return {
		"status": "ok",
		"company": company_name,
		"password": DEMO_PASSWORD,
		"created": created,
		"updated": updated,
	}


def _ensure_demo_user(row):
	email = row["email"]
	existing = frappe.db.exists("User", email)
	if existing:
		user = frappe.get_doc("User", email)
		created = False
	else:
		user = frappe.new_doc("User")
		user.email = email
		user.send_welcome_email = 0
		user.user_type = "System User"
		created = True

	user.first_name = row["first_name"]
	user.last_name = row["last_name"]
	user.username = email
	user.enabled = 1
	user.user_type = "System User"

	if created:
		user.insert(ignore_permissions=True)

	user.save(ignore_permissions=True)

	current_roles = {d.role for d in user.roles}
	missing_roles = [role for role in row["roles"] if role not in current_roles]
	if missing_roles:
		user.add_roles(*missing_roles)

	user.new_password = DEMO_PASSWORD
	user.save(ignore_permissions=True)

	return user.name, created


def rollback_demo_data():
	"""
	Remove demo users/employees and roll back Food Menu Item changes where possible.
	Safe to run multiple times.
	"""
	result = {
		"status": "ok",
		"deleted": {"users": [], "employees": [], "food_menu_items": []},
		"restored": {"food_menu_items": []},
		"skipped": {"food_menu_items": []},
	}

	for row in DEMO_USERS:
		employee_name = frappe.db.get_value("Employee", {"user_id": row["email"]}, "name")
		if employee_name and frappe.db.exists("Employee", employee_name):
			frappe.delete_doc("Employee", employee_name, ignore_permissions=True, force=1)
			result["deleted"]["employees"].append(employee_name)

		if frappe.db.exists("User", row["email"]):
			frappe.delete_doc("User", row["email"], ignore_permissions=True, force=1)
			result["deleted"]["users"].append(row["email"])

	for day, menu in DEMO_MENUS.items():
		names = frappe.get_all(
			"Food Menu Item",
			filters={
				"day": day,
				"breakfast_item": menu["breakfast_item"],
				"lunch_item": menu["lunch_item"],
				"dinner_item": menu["dinner_item"],
			},
			pluck="name",
		)

		for name in names:
			action = _rollback_food_menu_item(name)
			if action["action"] == "deleted":
				result["deleted"]["food_menu_items"].append(name)
			elif action["action"] == "restored":
				result["restored"]["food_menu_items"].append(name)
			else:
				result["skipped"]["food_menu_items"].append(name)

	frappe.db.commit()
	return result


def _ensure_demo_employee(row, company_name):
	existing = frappe.db.get_value("Employee", {"user_id": row["email"]}, "name")
	if existing:
		employee = frappe.get_doc("Employee", existing)
		created = False
	else:
		employee = frappe.new_doc("Employee")
		employee.naming_series = "HR-EMP-"
		employee.user_id = row["email"]
		created = True

	employee.first_name = row["first_name"]
	employee.last_name = row["last_name"]
	employee.gender = row["gender"]
	employee.date_of_birth = row["date_of_birth"]
	employee.date_of_joining = row["date_of_joining"]
	employee.status = "Active"
	employee.company = company_name

	if hasattr(employee, "custom_dietary_preference"):
		employee.custom_dietary_preference = row["dietary_preference"]

	if created:
		employee.insert(ignore_permissions=True)
	else:
		employee.save(ignore_permissions=True)

	return employee.name, created


def _ensure_food_menu_item(day, menu):
	existing = frappe.db.get_value("Food Menu Item", {"day": day}, "name")
	if existing:
		doc = frappe.get_doc("Food Menu Item", existing)
		created = False
	else:
		doc = frappe.new_doc("Food Menu Item")
		doc.day = day
		created = True

	doc.available = 1
	doc.breakfast_item = menu["breakfast_item"]
	doc.breakfast_description = menu["breakfast_description"]
	doc.lunch_item = menu["lunch_item"]
	doc.lunch_description = menu["lunch_description"]
	doc.dinner_item = menu["dinner_item"]
	doc.dinner_description = menu["dinner_description"]

	if created:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	return doc.name, created


def _resolve_company(company=None):
	if company and frappe.db.exists("Company", company):
		return company

	if frappe.db.exists("Company", DEFAULT_COMPANY):
		return DEFAULT_COMPANY

	companies = frappe.get_all("Company", pluck="name")
	non_test = [name for name in companies if not name.startswith("_Test")]

	if non_test:
		return non_test[0]

	if companies:
		return companies[0]

	frappe.throw("No Company record found. Please create a company before seeding demo data.")


def _rollback_food_menu_item(name):
	doc = frappe.get_doc("Food Menu Item", name)

	# If the record was created by the seed and not meaningfully edited later,
	# remove it entirely.
	if str(doc.creation) == str(doc.modified):
		frappe.delete_doc("Food Menu Item", name, ignore_permissions=True, force=1)
		return {"action": "deleted"}

	version_name = frappe.db.get_value(
		"Version",
		{"ref_doctype": "Food Menu Item", "docname": name},
		"name",
		order_by="creation desc",
	)

	if not version_name:
		return {"action": "skipped"}

	version = frappe.get_doc("Version", version_name)
	data = json.loads(version.data or "{}")
	changed = data.get("changed") or []

	restored = False
	for row in changed:
		if len(row) != 3:
			continue
		fieldname, old_value, new_value = row
		if (
			fieldname
			in {
				"breakfast_item",
				"breakfast_description",
				"lunch_item",
				"lunch_description",
				"dinner_item",
				"dinner_description",
				"available",
			}
			and getattr(doc, fieldname, None) == new_value
		):
			setattr(doc, fieldname, old_value)
			restored = True

	if not restored:
		return {"action": "skipped"}

	doc.save(ignore_permissions=True)
	return {"action": "restored"}
