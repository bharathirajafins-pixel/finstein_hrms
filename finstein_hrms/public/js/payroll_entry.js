frappe.ui.form.on("Payroll Entry", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;

		frm.add_custom_button(
			__("Check Payroll Readiness"),
			() => {
				if (!frm.doc.start_date || !frm.doc.end_date) {
					frappe.msgprint({
						title: "Missing Dates",
						indicator: "orange",
						message:
							"Please set the Start Date and End Date before running the readiness check.",
					});
					return;
				}

				frappe.call({
					method: "finstein_hrms.api.check_payroll_readiness",
					args: {
						start_date: frm.doc.start_date,
						end_date: frm.doc.end_date,
					},
					callback(r) {
						if (!r.message || !r.message.enabled) {
							frappe.msgprint(
								"Payroll readiness check is disabled in Finstein HRMS Settings."
							);
							return;
						}

						const d = r.message;
						const color = d.ready ? "green" : "red";
						const status = d.ready
							? "All checks passed. Safe to run payroll."
							: "Please resolve the items below before running payroll.";

						frappe.msgprint({
							title: __("Payroll Readiness Check"),
							indicator: color,
							message: `
                                <table style="width:100%;border-collapse:collapse;">
                                  <tr>
                                    <td style="padding:6px;border-bottom:1px solid #eee;">
                                      <b>Pending Leave Approvals</b>
                                    </td>
                                    <td style="padding:6px;border-bottom:1px solid #eee;color:${
										d.pending_leave_approvals > 0 ? "red" : "green"
									}">
                                      ${d.pending_leave_approvals}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td style="padding:6px;border-bottom:1px solid #eee;">
                                      <b>Pending Attendance Corrections</b>
                                    </td>
                                    <td style="padding:6px;border-bottom:1px solid #eee;color:${
										d.pending_attendance_corrections > 0 ? "red" : "green"
									}">
                                      ${d.pending_attendance_corrections}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td style="padding:6px;">
                                      <b>Unsynced Check-In Records</b>
                                    </td>
                                    <td style="padding:6px;color:${
										d.unsynced_checkins > 0 ? "red" : "green"
									}">
                                      ${d.unsynced_checkins}
                                    </td>
                                  </tr>
                                </table>
                                <br><b>${status}</b>
                            `,
						});
					},
				});
			},
			__("HR Tools")
		);
	},
});
