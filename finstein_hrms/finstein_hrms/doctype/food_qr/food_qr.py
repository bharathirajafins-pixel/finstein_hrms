# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FoodQR(Document):
	pass


@frappe.whitelist()
def generate_qr(name, force_regenerate=0):
	"""
	Generate/update QR for the selected Food QR record date + food type.
	Triggered from Food QR form button.
	"""
	doc = frappe.get_doc("Food QR", name)
	force_regenerate = int(force_regenerate or 0)

	generated_names = frappe.get_attr("finstein_hrms.scheduled_tasks.generate_food_qr_for_date")(
		target_date=doc.date,
		food_type=doc.food_type,
		force_regenerate=bool(force_regenerate),
	)

	if name not in generated_names:
		# Fallback: fetch record by unique key if rename/autoname changed.
		updated_name = frappe.db.get_value(
			"Food QR",
			{"date": doc.date, "food_type": doc.food_type},
			"name",
		)
		return {"name": updated_name}

	return {"name": name}
