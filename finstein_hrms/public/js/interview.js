frappe.ui.form.on('Interview', {

    // -----------------------------------------------
    // 🔄 REFRESH — runs on every form load/refresh
    // -----------------------------------------------
    refresh: function (frm) {

        // Set filter on interview_round based on selected interview_type
        frm.set_query('interview_round', function () {
            if (frm.doc.interview_type) {
                return {
                    filters: {
                        interview_type: frm.doc.interview_type
                    }
                };
            }
            // If no type selected, show all rounds (no filter)
            return {};
        });

    },

    // -----------------------------------------------
    // 📋 INTERVIEW TYPE CHANGED
    // -----------------------------------------------
    interview_type: function (frm) {

        // Update the round field filter to match the new type
        frm.set_query('interview_round', function () {
            if (frm.doc.interview_type) {
                return {
                    filters: {
                        interview_type: frm.doc.interview_type
                    }
                };
            }
            return {};
        });

        // Clear interview_round only if it belongs to a different type
        if (frm.doc.interview_round) {
            frappe.db.get_value(
                'Interview Round',
                frm.doc.interview_round,
                'interview_type',
                function (r) {
                    if (r && r.interview_type && r.interview_type !== frm.doc.interview_type) {
                        frm.set_value('interview_round', null);
                        frappe.show_alert({
                            message: __('Interview Round cleared as it did not match the selected Interview Type.'),
                            indicator: 'orange'
                        }, 4);
                    }
                }
            );
        }

    },

    // -----------------------------------------------
    // 🎯 INTERVIEW ROUND CHANGED
    // -----------------------------------------------
    interview_round: function (frm) {

        // Auto-fill interview_type from the selected round
        if (frm.doc.interview_round) {
            frappe.db.get_value(
                'Interview Round',
                frm.doc.interview_round,
                'interview_type',
                function (r) {
                    if (r && r.interview_type) {

                        // Only update if interview_type is different
                        if (frm.doc.interview_type !== r.interview_type) {
                            frm.set_value('interview_type', r.interview_type);
                            frappe.show_alert({
                                message: __('Interview Type has been auto-filled from the selected Round.'),
                                indicator: 'blue'
                            }, 4);
                        }

                        // Re-apply filter after auto-fill to keep dropdown in sync
                        frm.set_query('interview_round', function () {
                            return {
                                filters: {
                                    interview_type: r.interview_type
                                }
                            };
                        });

                    }
                }
            );
        } else {
            // If round is cleared, reset the filter to show all rounds
            frm.set_query('interview_round', function () {
                if (frm.doc.interview_type) {
                    return {
                        filters: {
                            interview_type: frm.doc.interview_type
                        }
                    };
                }
                return {};
            });
        }

    }

});