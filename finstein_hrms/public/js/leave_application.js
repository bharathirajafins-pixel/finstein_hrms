frappe.ui.form.on('Leave Application', {

    onload(frm) {
        toggle_time_fields(frm);
    },

    half_day(frm) {
        toggle_time_fields(frm);
    },

    half_day_date(frm) {
        toggle_time_fields(frm);
    },

    refresh(frm) {
        toggle_time_fields(frm);
    }

});

function toggle_time_fields(frm) {
    const today = frappe.datetime.get_today(); // "YYYY-MM-DD"
    const is_half_day = frm.doc.half_day;
    const half_day_date = frm.doc.half_day_date;

    // ─── Show for today AND future dates ───
    const show = is_half_day && half_day_date && (half_day_date >= today);

    // ─── Show / Hide ───
    frm.set_df_property('custom_from_time', 'hidden', !show);
    frm.set_df_property('custom_to_time', 'hidden', !show);

    // ─── Mandatory / Not Mandatory ───
    frm.set_df_property('custom_from_time', 'reqd', show ? 1 : 0);
    frm.set_df_property('custom_to_time', 'reqd', show ? 1 : 0);

    // ─── Clear values if hidden ───
    if (!show) {
        frm.set_value('custom_from_time', '');
        frm.set_value('custom_to_time', '');
    }

    frm.refresh_fields(['custom_from_time', 'custom_to_time']);
}