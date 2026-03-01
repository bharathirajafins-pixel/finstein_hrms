// ════════════════════════════════════════════════════════════════
// CLIENT SCRIPT: Leave Application - Show/Hide Time Fields
// ════════════════════════════════════════════════════════════════
// This script shows From Time and To Time fields only when Half Day is checked

frappe.ui.form.on('Leave Application', {
    // When form loads
    refresh: function(frm) {
        toggle_time_fields(frm);
    },
    
    // When half_day checkbox is clicked
    half_day: function(frm) {
        toggle_time_fields(frm);
        
        // Clear time values when unchecking half_day
        if (!frm.doc.half_day) {
            frm.set_value('custom_from_time', null);
            frm.set_value('custom_to_time', null);
        }
    }
});

// Function to show/hide time fields
function toggle_time_fields(frm) {
    if (frm.doc.half_day) {
        // Show time fields when half_day is checked
        frm.set_df_property('custom_from_time', 'hidden', 0);
        frm.set_df_property('custom_to_time', 'hidden', 0);
        
        // Optional: Make them NOT mandatory (they are optional)
        frm.set_df_property('custom_from_time', 'reqd', 0);
        frm.set_df_property('custom_to_time', 'reqd', 0);
    } else {
        // Hide time fields when half_day is unchecked
        frm.set_df_property('custom_from_time', 'hidden', 1);
        frm.set_df_property('custom_to_time', 'hidden', 1);
    }
    
    // Refresh the fields
    frm.refresh_field('custom_from_time');
    frm.refresh_field('custom_to_time');
}