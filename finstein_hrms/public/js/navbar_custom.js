// -----------------------------------------------
// FILE: your_app/public/js/navbar_custom.js
// DESIGN: Clean light theme, normal Frappe style
// -----------------------------------------------

$(function () {
    inject_navbar_items();
    inject_datetime_display();
    watch_unread_notifications();
});

frappe.router.on('change', function () {
    inject_navbar_items();
    inject_datetime_display();
});


// ══════════════════════════════════════════════
// 1. CUSTOM NAVBAR BUTTONS (Tasks, Calendar)
// ══════════════════════════════════════════════
function inject_navbar_items() {
    if ($('#custom-navbar-items').length) return;

    let $navbarNav = $('.navbar-nav.d-none.d-sm-flex');
    if (!$navbarNav.length) return;

    let $wrapper = $('<div id="custom-navbar-items"></div>');

    $wrapper.append(`
        <li class="nav-item">
            <a class="nav-link btn-link" href="/app/todo" title="My Tasks">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15"
                     viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 11l3 3L22 4"/>
                    <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
                </svg>
                <span style="font-size:12px;">Tasks</span>
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link btn-link" href="/app/event" title="Calendar">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15"
                     viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                    <line x1="16" y1="2" x2="16" y2="6"/>
                    <line x1="8" y1="2" x2="8" y2="6"/>
                    <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                <span style="font-size:12px;">Calendar</span>
            </a>
        </li>
    `);

    $navbarNav.prepend($wrapper);
}


// ══════════════════════════════════════════════
// 2. DATE / TIME DISPLAY
// ══════════════════════════════════════════════
function inject_datetime_display() {
    if ($('#custom-datetime').length) return;

    let $navbarNav = $('.navbar-nav.d-none.d-sm-flex');
    if (!$navbarNav.length) return;

    let $dateEl = $('<div id="custom-datetime"></div>');

    function updateTime() {
        let now = new Date();
        $dateEl.text(
            now.toLocaleDateString('en-IN', {
                weekday: 'short', day: '2-digit', month: 'short'
            }) + '  ' +
            now.toLocaleTimeString('en-IN', {
                hour: '2-digit', minute: '2-digit'
            })
        );
    }

    updateTime();
    setInterval(updateTime, 60000);
    $navbarNav.prepend($dateEl);
}


// ══════════════════════════════════════════════
// 3. NOTIFICATION BADGE — stays until read
// ══════════════════════════════════════════════
function watch_unread_notifications() {
    check_unread_count();
    setInterval(check_unread_count, 60000);
}

function check_unread_count() {
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Notification Log',
            filters: { for_user: frappe.session.user, read: 0 }
        },
        callback: function (r) {
            if (r && r.message !== undefined) {
                update_bell_badge(r.message);
            }
        }
    });
}

function update_bell_badge(count) {
    let $bell = $('.notifications-icon');
    let $badge = $bell.find('.badge');

    if (count > 0) {
        let label = count > 99 ? '99+' : count;
        if ($badge.length) {
            $badge.text(label).show();
        } else {
            $bell.css('position', 'relative').append(
                `<span class="badge">${label}</span>`
            );
        }
    } else {
        $badge.hide().text('');
    }
}


// ══════════════════════════════════════════════
// 4. NOTIFICATION DROPDOWN HEADER
//    with "Mark all read" button
// ══════════════════════════════════════════════
$(document).on('click', '.notifications-icon', function () {
    setTimeout(function () {
        let $list = $('.notifications-list');
        if (!$list.length) return;

        // Add header only once
        if (!$list.find('.custom-notif-header').length) {
            $list.prepend(`
                <div class="custom-notif-header" style="
                    padding: 10px 14px;
                    border-bottom: 1px solid #e8eaed;
                    background: #fff;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                ">
                    <span style="font-size:13px; font-weight:600; color:#333;">
                        🔔 Notifications
                    </span>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <button id="mark-all-read-btn" style="
                            background: #f0f3f8;
                            border: 1px solid #dde1e8;
                            color: #555;
                            font-size: 11px;
                            border-radius: 4px;
                            padding: 3px 9px;
                            cursor: pointer;
                            transition: background 0.15s;
                        ">Mark all read</button>
                        <a href="/app/notification-log"
                           style="font-size:11px; color:#4c7ef3; text-decoration:none;">
                            View All
                        </a>
                    </div>
                </div>
            `);
        }

        // Refresh count after opening
        setTimeout(check_unread_count, 800);
    }, 250);
});


// Mark all as read handler
$(document).on('click', '#mark-all-read-btn', function (e) {
    e.stopPropagation();
    frappe.call({
        method: 'frappe.desk.doctype.notification_log.notification_log.mark_all_as_read',
        callback: function () {
            update_bell_badge(0);
            $('.notifications-list .notification-item')
                .removeClass('unread')
                .addClass('read')
                .attr('data-read', '1');
            frappe.show_alert({
                message: __('All notifications marked as read.'),
                indicator: 'green'
            }, 3);
        }
    });
});