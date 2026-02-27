$(document).ready(function () {
    var checkReady = setInterval(function () {
        if (
            typeof frappe !== "undefined" &&
            frappe.session &&
            frappe.session.user &&
            frappe.session.user !== "Guest"
        ) {
            clearInterval(checkReady);
            initFinNotificationPopup();
        }
    }, 500);
});

function initFinNotificationPopup() {
    if (window.__fin_notif_popup_init) return;
    window.__fin_notif_popup_init = true;

    var STORAGE_KEY = "shown_notif_ids_v2:" + frappe.session.user;

    // ── CSS ──────────────────────────────────────────────────────────────────
    if (!document.getElementById("fin-notif-style")) {
        $("head").append(
            '<style id="fin-notif-style">' +

            '#notif-popup-container {' +
            '  position: fixed;' +
            '  bottom: 24px;' +
            '  right: 24px;' +
            '  z-index: 99999;' +
            '  display: flex;' +
            '  flex-direction: column;' +
            '  gap: 8px;' +
            '  width: 340px;' +
            '  pointer-events: none;' +
            '}' +

            '.notif-toast {' +
            '  pointer-events: all;' +
            '  background: #ffffff;' +
            '  border-radius: 10px;' +
            '  box-shadow: 0 8px 24px rgba(0,0,0,0.13), 0 2px 6px rgba(0,0,0,0.07);' +
            '  padding: 14px;' +
            '  display: flex;' +
            '  align-items: flex-start;' +
            '  gap: 10px;' +
            '  cursor: pointer;' +
            '  border: 1px solid #ebebeb;' +
            '  position: relative;' +
            '  overflow: hidden;' +
            '  animation: notif-slide-in 0.3s cubic-bezier(0.16,1,0.3,1);' +
            '  transition: box-shadow 0.2s, transform 0.2s;' +
            '}' +

            '.notif-toast:hover {' +
            '  box-shadow: 0 12px 32px rgba(0,0,0,0.16);' +
            '  transform: translateY(-2px);' +
            '}' +

            '.notif-toast-avatar {' +
            '  width: 38px;' +
            '  height: 38px;' +
            '  border-radius: 50%;' +
            '  background: linear-gradient(135deg, #f5a623, #e07b2a);' +
            '  display: flex;' +
            '  align-items: center;' +
            '  justify-content: center;' +
            '  font-size: 13px;' +
            '  font-weight: 700;' +
            '  color: #fff;' +
            '  flex-shrink: 0;' +
            '  text-transform: uppercase;' +
            '}' +

            '.notif-toast-content {' +
            '  flex: 1;' +
            '  min-width: 0;' +
            '}' +

            '.notif-toast-title {' +
            '  font-size: 13px;' +
            '  font-weight: 600;' +
            '  color: #1a1a1a;' +
            '  margin-bottom: 3px;' +
            '  white-space: nowrap;' +
            '  overflow: hidden;' +
            '  text-overflow: ellipsis;' +
            '}' +

            '.notif-toast-sub {' +
            '  font-size: 12px;' +
            '  color: #6b7280;' +
            '  white-space: nowrap;' +
            '  overflow: hidden;' +
            '  text-overflow: ellipsis;' +
            '}' +

            '.notif-toast-time {' +
            '  font-size: 11px;' +
            '  color: #aaa;' +
            '  margin-top: 4px;' +
            '}' +

            '.notif-toast-dot {' +
            '  width: 8px;' +
            '  height: 8px;' +
            '  border-radius: 50%;' +
            '  background: #5e64ff;' +
            '  flex-shrink: 0;' +
            '  margin-top: 5px;' +
            '}' +

            '.notif-toast-close {' +
            '  background: transparent;' +
            '  border: none;' +
            '  color: #bbb;' +
            '  font-size: 15px;' +
            '  cursor: pointer;' +
            '  line-height: 1;' +
            '  padding: 0;' +
            '  flex-shrink: 0;' +
            '  opacity: 0;' +
            '  transition: opacity 0.15s, color 0.15s;' +
            '}' +

            '.notif-toast:hover .notif-toast-close {' +
            '  opacity: 1;' +
            '}' +

            '.notif-toast-close:hover {' +
            '  color: #333;' +
            '}' +

            '.notif-toast-progress {' +
            '  position: absolute;' +
            '  bottom: 0;' +
            '  left: 0;' +
            '  height: 3px;' +
            '  background: #5e64ff;' +
            '  border-radius: 0 0 10px 10px;' +
            '  width: 100%;' +
            '  animation: notif-progress 3s linear forwards;' +
            '}' +

            '@keyframes notif-slide-in {' +
            '  from { opacity: 0; transform: translateX(60px) scale(0.96); }' +
            '  to   { opacity: 1; transform: translateX(0) scale(1); }' +
            '}' +

            '@keyframes notif-progress {' +
            '  from { width: 100%; }' +
            '  to   { width: 0%; }' +
            '}' +

            '</style>'
        );
    }

    // ── Container ─────────────────────────────────────────────────────────────
    if (!document.getElementById("notif-popup-container")) {
        $("body").append('<div id="notif-popup-container"></div>');
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    function escapeHtml(val) {
        return String(val || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function getInitials(name) {
        return String(name || "?")
            .split(" ")
            .slice(0, 2)
            .map(function (w) { return w[0] || ""; })
            .join("")
            .toUpperCase();
    }

    function timeAgo(dateStr) {
        if (!dateStr) return "just now";
        var diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
        if (diff < 60)    return "just now";
        if (diff < 3600)  return Math.floor(diff / 60) + " min ago";
        if (diff < 86400) return Math.floor(diff / 3600) + " hr ago";
        return Math.floor(diff / 86400) + " days ago";
    }

    function getShownList() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
        catch (e) { return []; }
    }

    function isAlreadyShown(id) {
        return getShownList().indexOf(id) !== -1;
    }

    function markAsShown(id) {
        var shown = getShownList();
        if (shown.indexOf(id) === -1) {
            shown.push(id);
            if (shown.length > 200) shown.splice(0, shown.length - 200);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(shown));
        }
    }

    // ── Show one toast ────────────────────────────────────────────────────────
    function showToast(notif) {
        if (!notif || !notif.name || isAlreadyShown(notif.name)) return;

        var subject  = escapeHtml(notif.subject  || "New Notification");
        var fromUser = escapeHtml(notif.from_user || notif.sender || "System");

        var toast = $(
            '<div class="notif-toast" data-id="' + escapeHtml(notif.name) + '">' +
                '<div class="notif-toast-avatar">' + getInitials(fromUser) + '</div>' +
                '<div class="notif-toast-content">' +
                    '<div class="notif-toast-title">' + subject + '</div>' +
                    '<div class="notif-toast-sub">'   + fromUser + '</div>' +
                    '<div class="notif-toast-time">'  + timeAgo(notif.creation) + '</div>' +
                '</div>' +
                '<div class="notif-toast-dot"></div>' +
                '<button class="notif-toast-close" title="Dismiss">&#x2715;</button>' +
                '<div class="notif-toast-progress"></div>' +
            '</div>'
        );

        // click toast → open document
        toast.on("click", function (e) {
            if ($(e.target).hasClass("notif-toast-close")) return;
            if (notif.document_type && notif.document_name) {
                frappe.set_route("Form", notif.document_type, notif.document_name);
            }
            toast.fadeOut(200, function () { toast.remove(); });
        });

        // click ✕ → dismiss
        toast.find(".notif-toast-close").on("click", function (e) {
            e.stopPropagation();
            toast.fadeOut(200, function () { toast.remove(); });
        });

        $("#notif-popup-container").prepend(toast);
        markAsShown(notif.name);

        // auto dismiss after 3s
        setTimeout(function () {
            toast.fadeOut(300, function () { toast.remove(); });
        }, 3000);
    }

    // ── Render unshown list ───────────────────────────────────────────────────
    function renderUnshown(rows, stagger) {
        var items = (rows || [])
            .filter(function (n) { return n && n.name && !isAlreadyShown(n.name); })
            .reverse();

        items.forEach(function (notif, i) {
            setTimeout(function () { showToast(notif); }, stagger ? i * 350 : 0);
        });
    }

    // ── Fetch from Frappe API ─────────────────────────────────────────────────
    function fetchAndShow(limit, stagger) {
        frappe.call({
            method: "frappe.desk.doctype.notification_log.notification_log.get_notification_logs",
            args: { limit: limit || 30 },
            callback: function (r) {
                var rows = (r && r.message && r.message.notification_logs) || [];
                renderUnshown(rows, stagger);
            },
            error: function () {
                // fallback
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Notification Log",
                        filters: { for_user: frappe.session.user },
                        fields: ["name", "subject", "email_content",
                                 "document_type", "document_name",
                                 "creation", "read", "from_user"],
                        order_by: "creation desc",
                        limit_page_length: limit || 30
                    },
                    callback: function (rr) {
                        renderUnshown((rr && rr.message) || [], stagger);
                    }
                });
            }
        });
    }

    // ── Start ─────────────────────────────────────────────────────────────────
    fetchAndShow(30, true);

    // poll every 8 seconds
    setInterval(function () { fetchAndShow(30, false); }, 6000);

    // when user returns to tab
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) fetchAndShow(10, false);
    });

    // when window gets focus
    window.addEventListener("focus", function () {
        fetchAndShow(30, false);
    });

    // realtime push
    frappe.realtime.on("notification", function () {
        setTimeout(function () { fetchAndShow(30, false); }, 400);
    });
}
