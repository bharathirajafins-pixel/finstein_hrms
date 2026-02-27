frappe.ui.form.on('Interview', {

    // -----------------------------------------------
    // 🔄 REFRESH — runs on every form load / refresh
    // -----------------------------------------------
    refresh: function (frm) {

        // Set filter on interview_round based on already selected custom_interview_type
        frm.set_query('interview_round', function () {
            if (frm.doc.custom_interview_type) {
                return {
                    filters: { interview_type: frm.doc.custom_interview_type }
                };
            }
            return {};
        });

        // Make custom_interview_type mandatory visually
        frm.set_df_property('custom_interview_type', 'reqd', 1);

        // If custom_interview_type is not set, disable interview_round to guide the user
        if (!frm.doc.custom_interview_type) {
            frm.set_df_property('interview_round', 'read_only', 1);
            frm.set_df_property('interview_round', 'description', 'Please select Interview Type first');
        } else {
            frm.set_df_property('interview_round', 'read_only', 0);
            frm.set_df_property('interview_round', 'description', '');
        }
    },

    // -----------------------------------------------
    // 📋 CUSTOM INTERVIEW TYPE CHANGED — user selects type first
    // -----------------------------------------------
    custom_interview_type: function (frm) {

        if (frm.doc.custom_interview_type) {
            // Enable interview_round now that type is selected
            frm.set_df_property('interview_round', 'read_only', 0);
            frm.set_df_property('interview_round', 'description', '');

            // Apply filter on interview_round to match selected type
            frm.set_query('interview_round', function () {
                return {
                    filters: { interview_type: frm.doc.custom_interview_type }
                };
            });

            // Clear interview_round only if it belongs to a different type
            if (frm.doc.interview_round) {
                frappe.db.get_value(
                    'Interview Round',
                    frm.doc.interview_round,
                    'interview_type',  // ✅ Only fetch interview_type — a standard field
                    function (r) {
                        if (r && r.interview_type && r.interview_type !== frm.doc.custom_interview_type) {
                            frm.set_value('interview_round', null);
                            frappe.show_alert({
                                message: __('Interview Round was cleared because it does not belong to the selected Interview Type.'),
                                indicator: 'orange'
                            }, 5);
                        }
                    }
                );
            }

        } else {
            // Type cleared — disable and clear the round field
            frm.set_df_property('interview_round', 'read_only', 1);
            frm.set_df_property('interview_round', 'description', 'Please select Interview Type first');
            frm.set_value('interview_round', null);

            // Reset filter to show all rounds
            frm.set_query('interview_round', function () {
                return {};
            });
        }
    },

    // -----------------------------------------------
    // 🎯 INTERVIEW ROUND CHANGED
    // -----------------------------------------------
    interview_round: function (frm) {

        if (frm.doc.interview_round) {
            // ✅ Only fetch 'interview_type' — a standard field on Interview Round
            // ❌ Do NOT fetch 'round_order' here — it's a custom field and blocked by Frappe client API
            frappe.db.get_value(
                'Interview Round',
                frm.doc.interview_round,
                'interview_type',
                function (r) {
                    if (r && r.interview_type) {

                        // Auto-fill custom_interview_type if not set or mismatched
                        if (!frm.doc.custom_interview_type || frm.doc.custom_interview_type !== r.interview_type) {
                            frm.set_value('custom_interview_type', r.interview_type);
                            frappe.show_alert({
                                message: __('Interview Type auto-filled from selected Round.'),
                                indicator: 'blue'
                            }, 4);
                        }

                        // Re-apply filter to stay in sync with selected type
                        frm.set_query('interview_round', function () {
                            return {
                                filters: { interview_type: r.interview_type }
                            };
                        });

                        // Ensure round field is enabled
                        frm.set_df_property('interview_round', 'read_only', 0);
                        frm.set_df_property('interview_round', 'description', '');
                    }
                }
            );
        }
    }

});