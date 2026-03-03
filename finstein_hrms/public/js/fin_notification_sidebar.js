$(document).ready(function () {

    var checkReady = setInterval(function () {
        if (
            typeof frappe !== "undefined" &&
            frappe.session &&
            frappe.session.user &&
            frappe.session.user !== "Guest"
        ) {
            clearInterval(checkReady);
            initFinNotificationSidebar();
        }
    }, 500);

});

function initFinNotificationSidebar() {

    if (window.__fin_notif_sidebar_init) return;
    window.__fin_notif_sidebar_init = true;

    var SIDEBAR_WIDTH = 280; // Fixed sidebar width — do NOT change this

    /* ══════════════════════════════════════════
       CSS
    ══════════════════════════════════════════ */

    if (!document.getElementById("fin-notif-style")) {
        $("head").append(`
            <style id="fin-notif-style">

            body {
                overflow-x: hidden;
            }

            /*
             * EXPAND the Frappe workspace content to fill all available space.
             * Frappe by default limits content width with max-width.
             * We override that so content stretches to use the empty left/right gaps.
             * Then we add padding-right equal to sidebar width so sidebar doesn't overlap.
             */

            /* Remove Frappe's default max-width restriction on main layout */
            .page-container {
                max-width: 100% !important;
                width: 100% !important;
                padding-right: ${SIDEBAR_WIDTH}px !important;
                box-sizing: border-box !important;
            }

            /* Expand the inner layout wrapper */
            .layout-main,
            .layout-main-section,
            .layout-main-section-wrapper {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Expand workspace content area */
            .workspace-container,
            .widget-group,
            .modules-section {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* ── Fixed Sidebar — width stays 280px always ── */
            #fin-notif-sidebar {
                position: fixed;
                top: 56px;
                right: 0;
                width: ${SIDEBAR_WIDTH}px;
                height: calc(100vh - 56px);
                background: #ffffff;
                border-left: 1px solid #e2e8f0;
                box-shadow: -2px 0 12px rgba(0, 0, 0, 0.05);
                z-index: 999;
                display: flex;
                flex-direction: column;
                font-family: inherit;
            }

            /* ── Header ── */
            .fin-notif-header {
                padding: 12px 14px;
                border-bottom: 1px solid #f1f5f9;
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #f8fafc;
                flex-shrink: 0;
            }

            .fin-notif-header-title {
                font-size: 11px;
                font-weight: 700;
                color: #64748b;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .fin-notif-badge {
                background: #ef4444;
                color: #fff;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 6px;
                border-radius: 20px;
                min-width: 18px;
                text-align: center;
                display: inline-block;
                flex-shrink: 0;
                margin-left: 6px;
                transition: transform 0.15s ease;
            }

            .fin-notif-badge.pop {
                transform: scale(1.5);
            }

            .fin-notif-badge[data-count="0"] {
                display: none;
            }

            /* ── Scrollable List ── */
            .fin-notif-list {
                flex: 1;
                overflow-y: auto;
                scroll-behavior: smooth;
            }

            .fin-notif-list::-webkit-scrollbar {
                width: 3px;
            }

            .fin-notif-list::-webkit-scrollbar-thumb {
                background: #e2e8f0;
                border-radius: 4px;
            }

            /* ── Each Item ── */
            .fin-notif-item {
                padding: 10px 14px 10px 16px;
                border-bottom: 1px solid #f8fafc;
                cursor: pointer;
                transition: background 0.12s ease;
                position: relative;
            }

            .fin-notif-item:hover {
                background: #eff6ff;
            }

            .fin-notif-item::before {
                content: "";
                position: absolute;
                left: 0;
                top: 6px;
                bottom: 6px;
                width: 3px;
                background: #3b82f6;
                border-radius: 0 2px 2px 0;
            }

            .fin-notif-item.new-flash {
                animation: finFlash 1.8s ease forwards;
            }

            @keyframes finFlash {
                0%   { background: #dbeafe; }
                65%  { background: #dbeafe; }
                100% { background: transparent; }
            }

            .fin-notif-title {
                font-size: 12px;
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 3px;
                line-height: 1.45;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }

            .fin-notif-meta {
                font-size: 10px;
                color: #94a3b8;
            }

            /* ── Empty State ── */
            .fin-notif-empty {
                padding: 40px 16px;
                text-align: center;
                color: #94a3b8;
                font-size: 12px;
                line-height: 1.8;
            }

            .fin-notif-empty svg {
                display: block;
                margin: 0 auto 10px;
                opacity: 0.25;
            }

            /* ── Footer ── */
            .fin-notif-footer {
                padding: 8px 14px;
                border-top: 1px solid #f1f5f9;
                text-align: center;
                flex-shrink: 0;
                background: #f8fafc;
            }

            .fin-notif-mark-all {
                font-size: 11px;
                color: #3b82f6;
                cursor: pointer;
                font-weight: 600;
            }

            .fin-notif-mark-all:hover {
                text-decoration: underline;
                color: #2563eb;
            }

            </style>
        `);
    }

    /* ══════════════════════════════════════════
       HTML
    ══════════════════════════════════════════ */

    if (!document.getElementById("fin-notif-sidebar")) {
        $("body").append(`
            <div id="fin-notif-sidebar">
                <div class="fin-notif-header">
                    <span class="fin-notif-header-title">Notification</span>
                    <span class="fin-notif-badge" id="fin-notif-badge" data-count="0">0</span>
                </div>
                <div class="fin-notif-list" id="fin-notif-list"></div>
                <div class="fin-notif-footer">
                    <span class="fin-notif-mark-all" id="fin-notif-mark-all">Mark all as read</span>
                </div>
            </div>
        `);
    }

    /* ══════════════════════════════════════════
       Helpers
    ══════════════════════════════════════════ */

    function escapeHtml(val) {
        return String(val || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function resolveNotificationRoute(n) {
        if (n.document_type && n.document_name) {
            return ["Form", n.document_type, n.document_name];
        }

        if (n.link) {
            var cleanLink = String(n.link).replace(/^https?:\/\/[^/]+/i, "");
            var match =
                cleanLink.match(/\/app\/form\/([^/]+)\/([^/?#]+)/i) ||
                cleanLink.match(/\/app\/([^/]+)\/([^/?#]+)/i);

            if (match) {
                return [
                    "Form",
                    decodeURIComponent(match[1]).replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); }),
                    decodeURIComponent(match[2]),
                ];
            }
        }

        return null;
    }

    function timeAgo(dateStr) {
        if (!dateStr) return "just now";
        var diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
        if (diff < 60)    return "just now";
        if (diff < 3600)  return Math.floor(diff / 60) + " min ago";
        if (diff < 86400) return Math.floor(diff / 3600) + " hr ago";
        return Math.floor(diff / 86400) + " days ago";
    }

    function setBadge(count) {
        $("#fin-notif-badge").text(count).attr("data-count", count);
    }

    function animateBadge() {
        var $b = $("#fin-notif-badge");
        $b.addClass("pop");
        setTimeout(function () { $b.removeClass("pop"); }, 250);
    }

    function showEmptyState() {
        $("#fin-notif-list").html(`
            <div class="fin-notif-empty">
                <svg width="36" height="36" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118
                           14.158V11a6 6 0 10-12 0v3.159c0 .538-.214
                           1.055-.595 1.436L4 17h5m6 0v1a3 3 0
                           11-6 0v-1m6 0H9"/>
                </svg>
                All caught up!<br>No unread notifications.
            </div>
        `);
    }

    /* ══════════════════════════════════════════
       Render
    ══════════════════════════════════════════ */

    var _prevCount = 0;

    function renderNotifications(rows, isNewArrival) {
        var $list = $("#fin-notif-list");
        $list.empty();
        setBadge(rows.length);

        if (isNewArrival && rows.length > _prevCount) animateBadge();
        _prevCount = rows.length;

        if (!rows.length) { showEmptyState(); return; }

        rows.forEach(function (n, index) {
            var isNew = isNewArrival && index === 0;

            var $item = $(`
                <div class="fin-notif-item ${isNew ? "new-flash" : ""}">
                    <div class="fin-notif-title">${escapeHtml(n.subject || "Notification")}</div>
                    <div class="fin-notif-meta">${timeAgo(n.creation)}</div>
                </div>
            `);

            $item.on("click", function () {
                var route = resolveNotificationRoute(n);

                if (route) {
                    frappe.set_route.apply(frappe, route);
                } else {
                    frappe.set_route("Form", "Notification Log", n.name);
                }

                frappe.call({
                    method: "frappe.desk.doctype.notification_log.notification_log.mark_as_read",
                    args: { docname: n.name },
                    callback: function () {
                        $item.slideUp(180, function () {
                            $item.remove();
                            _prevCount = Math.max(0, _prevCount - 1);
                            setBadge(_prevCount);
                            if (_prevCount === 0) showEmptyState();
                        });
                    }
                });
            });

            $list.append($item);
        });
    }

    /* ══════════════════════════════════════════
       Fetch — UNREAD ONLY
    ══════════════════════════════════════════ */

    function fetchNotifications(isNewArrival) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Notification Log",
                filters: { for_user: frappe.session.user, read: 0 },
                fields: ["name", "subject", "document_type", "document_name", "link", "creation"],
                order_by: "creation desc",
                limit_page_length: 50
            },
            callback: function (r) {
                renderNotifications(r.message || [], isNewArrival || false);
            }
        });
    }

    /* ══════════════════════════════════════════
       Mark All as Read
    ══════════════════════════════════════════ */

    $(document).on("click", "#fin-notif-mark-all", function () {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Notification Log",
                filters: { for_user: frappe.session.user, read: 0 },
                fields: ["name"],
                limit_page_length: 100
            },
            callback: function (r) {
                var unread = r.message || [];
                if (!unread.length) return;
                var done = 0;
                unread.forEach(function (n) {
                    frappe.call({
                        method: "frappe.desk.doctype.notification_log.notification_log.mark_as_read",
                        args: { docname: n.name },
                        callback: function () {
                            done++;
                            if (done === unread.length) fetchNotifications(false);
                        }
                    });
                });
            }
        });
    });

    /* ══════════════════════════════════════════
       Init + Realtime
    ══════════════════════════════════════════ */

    fetchNotifications(false);

    setInterval(function () { fetchNotifications(false); }, 60000);

    frappe.realtime.on("notification", function () {
        setTimeout(function () { fetchNotifications(true); }, 300);
    });

}
