// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Food Count", {
	refresh(frm) {
		set_defaults_and_load_menu(frm);
		set_status_field_access(frm);
	},
	order_date(frm) {
		load_menu_for_selected_date(frm);
	},
	breakfast_selected(frm) {
		apply_slot_selection(
			frm,
			"breakfast_selected",
			"breakfast",
			"breakfast_item",
			"Breakfast"
		);
	},
	lunch_selected(frm) {
		apply_slot_selection(frm, "lunch_selected", "lunch", "lunch_item", "Lunch");
	},
	dinner_selected(frm) {
		apply_slot_selection(frm, "dinner_selected", "dinner", "dinner_item", "Dinner");
	},
});

function set_defaults_and_load_menu(frm) {
	frm.set_df_property("user", "read_only", 1);
	frm.set_df_property("order_date", "read_only", 1);
	frm.set_df_property("breakfast", "read_only", 1);
	frm.set_df_property("lunch", "read_only", 1);
	frm.set_df_property("dinner", "read_only", 1);

	if (!frm.doc.user) {
		frm.set_value("user", frappe.session.user);
	}
	if (!frm.doc.order_date && frm.is_new()) {
		frm.set_value("order_date", frappe.datetime.add_days(frappe.datetime.get_today(), 1));
	}

	load_menu_for_selected_date(frm);
}

function set_status_field_access(frm) {
	const can_edit_status = frappe.user.has_role("HR Manager");

	["breakfast_status", "lunch_status", "dinner_status"].forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", can_edit_status ? 0 : 1);
	});
}

function load_menu_for_selected_date(frm) {
	if (!frm.doc.order_date) {
		return;
	}

	frappe.call({
		method: "finstein_hrms.finstein_hrms.doctype.food_count.food_count.get_menu_for_date",
		args: { order_date: frm.doc.order_date },
		callback: function (r) {
			frm._menu_items = r.message || {};

			apply_slot_selection(
				frm,
				"breakfast_selected",
				"breakfast",
				"breakfast_item",
				"Breakfast"
			);
			apply_slot_selection(frm, "lunch_selected", "lunch", "lunch_item", "Lunch");
			apply_slot_selection(frm, "dinner_selected", "dinner", "dinner_item", "Dinner");
			sync_slot_ui(frm, "breakfast_selected", "breakfast_item", "Breakfast");
			sync_slot_ui(frm, "lunch_selected", "lunch_item", "Lunch");
			sync_slot_ui(frm, "dinner_selected", "dinner_item", "Dinner");
		},
	});
}

function apply_slot_selection(frm, checkField, itemField, menuField, label) {
	const selected = !!frm.doc[checkField];
	const menuItems = frm._menu_items || {};
	const menuItem = menuItems[menuField] || "";

	if (selected && !menuItem) {
		frappe.msgprint(`${label} menu is not available for selected date.`);
		frm.set_value(checkField, 0);
		frm.set_value(itemField, "");
		return;
	}

	// Always show menu item; checkbox decides whether it is counted as ordered.
	frm.set_value(itemField, menuItem);
}

function sync_slot_ui(frm, checkField, menuField, slotLabel) {
	const menuItems = frm._menu_items || {};
	const menuItem = menuItems[menuField] || "";
	const hasMenu = !!menuItem;

	frm.toggle_enable(checkField, hasMenu);
	frm.set_df_property(
		checkField,
		"label",
		hasMenu ? `Select ${slotLabel} (${menuItem})` : `Select ${slotLabel} (Not Available)`
	);

	if (!hasMenu && frm.doc[checkField]) {
		frm.set_value(checkField, 0);
	}
}
