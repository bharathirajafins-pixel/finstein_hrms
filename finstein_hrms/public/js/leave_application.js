frappe.ui.form.on("Leave Application", {
	onload(frm) {
		sync_leave_approver_requirement(frm);
		sync_leave_approver_requirement_after_ajax(frm);
	},

	refresh(frm) {
		sync_leave_approver_requirement(frm);
		sync_leave_approver_requirement_after_ajax(frm);
		toggle_time_fields(frm);
		add_withdraw_button(frm);
	},

	employee(frm) {
		sync_leave_approver_requirement(frm);
		sync_leave_approver_requirement_after_ajax(frm);
	},

	before_workflow_action(frm) {
		return sync_leave_approver_requirement(frm);
	},

	async validate(frm) {
		await validate_leave_approver_requirement(frm);
	},

	half_day(frm) {
		toggle_time_fields(frm);

		if (!frm.doc.half_day) {
			frm.set_value("custom_from_time", null);
			frm.set_value("custom_to_time", null);
		}
	},
});

async function sync_leave_approver_requirement(frm) {
	if (!frm.doc.employee) return;

	const isMandatory = await frappe.db.get_single_value(
		"HR Settings",
		"leave_approver_mandatory_in_leave_application"
	);

	if (!isMandatory) {
		frm.set_df_property("leave_approver", "reqd", 0);
		frm.__is_team_leader_applicant = false;
		return;
	}

	const employeeRes = await frappe.db.get_value("Employee", frm.doc.employee, "user_id");
	const employeeUser = employeeRes?.message?.user_id;

	if (!employeeUser) {
		frm.set_df_property("leave_approver", "reqd", 0);
		frm.__is_team_leader_applicant = false;
		return;
	}

	let isTeamLeaderApplicant = false;

	if (employeeUser === frappe.session.user) {
		isTeamLeaderApplicant = frappe.user.has_role("Team Leader");
	} else {
		const roleRes = await frappe.call({
			method: "finstein_hrms.api.is_employee_team_leader",
			args: { employee: frm.doc.employee },
		});
		isTeamLeaderApplicant = !!roleRes.message?.is_team_leader;
	}

	frm.__is_team_leader_applicant = isTeamLeaderApplicant;
	frm.set_df_property("leave_approver", "reqd", 0);

	if (isTeamLeaderApplicant && frm.doc.leave_approver) {
		await frm.set_value("leave_approver", "");
		await frm.set_value("leave_approver_name", "");
	}
}

async function validate_leave_approver_requirement(frm) {
	if (!frm.doc.employee) return;

	const isMandatory = await frappe.db.get_single_value(
		"HR Settings",
		"leave_approver_mandatory_in_leave_application"
	);

	if (!isMandatory) return;

	if (!is_initial_leave_request_stage(frm)) return;

	if (frm.__is_team_leader_applicant === undefined) {
		await sync_leave_approver_requirement(frm);
	}

	if (frm.__is_team_leader_applicant) return;

	if (!frm.doc.leave_approver) {
		frappe.throw("Leave Approver is mandatory for this employee.");
	}
}

function is_initial_leave_request_stage(frm) {
	return !frm.doc.workflow_state || frm.doc.workflow_state === "Draft";
}

function sync_leave_approver_requirement_after_ajax(frm) {
	frappe.after_ajax(() => {
		if (!frm.is_destroyed) {
			sync_leave_approver_requirement(frm);
		}
	});
}

function toggle_time_fields(frm) {
	const showTimeFields = !!frm.doc.half_day;

	frm.set_df_property("custom_from_time", "hidden", showTimeFields ? 0 : 1);
	frm.set_df_property("custom_to_time", "hidden", showTimeFields ? 0 : 1);

	if (showTimeFields) {
		frm.set_df_property("custom_from_time", "reqd", 0);
		frm.set_df_property("custom_to_time", "reqd", 0);
	}

	frm.refresh_field("custom_from_time");
	frm.refresh_field("custom_to_time");
}

function add_withdraw_button(frm) {
	const withdrawable = ["Pending", "Pending HR Approve"];

	if (!withdrawable.includes(frm.doc.workflow_state)) return;
	if (frm.doc.owner !== frappe.session.user) return;

	frappe.db
		.get_single_value("Finstein HRMS Settings", "enable_leave_withdrawal")
		.then((enabled) => {
			if (!enabled) return;

			frm.add_custom_button(
				__("Withdraw Application"),
				() => {
					frappe.confirm(
						"Are you sure you want to withdraw this leave application? This action cannot be undone.",
						() => {
							frappe.call({
								method: "finstein_hrms.api.withdraw_leave_application",
								args: { docname: frm.doc.name },
								callback(r) {
									if (!r.exc) {
										frappe.show_alert({
											message: "Leave application withdrawn successfully.",
											indicator: "green",
										});
										frm.reload_doc();
									}
								},
							});
						}
					);
				},
				__("Actions")
			);
		});
}
