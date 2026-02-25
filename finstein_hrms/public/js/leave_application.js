frappe.ui.form.on('Leave Application', {

    // ─── Trigger on form load ───
    onload(frm) {
        toggle_time_fields(frm);
    },

    // ─── Trigger when half_day checkbox changes ───
    half_day(frm) {
        toggle_time_fields(frm);
    },

    // ─── Trigger when half_day_date changes ───
    half_day_date(frm) {
        toggle_time_fields(frm);
    },

    // ─── Trigger on form refresh ───
    refresh(frm) {
        toggle_time_fields(frm);
    }

});

function toggle_time_fields(frm) {
    const today = frappe.datetime.get_today(); // "YYYY-MM-DD"
    const is_half_day = frm.doc.half_day;
    const half_day_date = frm.doc.half_day_date;

    // Show fields only if half_day is checked AND date is today
    const show = is_half_day && (half_day_date === today);

    // ─── Show / Hide ───
    frm.set_df_property('from_time', 'hidden', !show);
    frm.set_df_property('to_time', 'hidden', !show);

    // ─── Mandatory / Not Mandatory ───
    frm.set_df_property('from_time', 'reqd', show ? 1 : 0);
    frm.set_df_property('to_time', 'reqd', show ? 1 : 0);

    // ─── Clear values if hidden ───
    if (!show) {
        frm.set_value('from_time', '');
        frm.set_value('to_time', '');
    }

    frm.refresh_fields(['from_time', 'to_time']);
}