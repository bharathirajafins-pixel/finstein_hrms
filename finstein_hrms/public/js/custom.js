function initFinNotificationPopup() {
	if (window.__fin_notif_popup_init) return;
	window.__fin_notif_popup_init = true;

	const STORAGE_KEY = `shown_notif_ids:${frappe.session.user}`;

	function ensureContainer() {
		if (!document.getElementById("notif-popup-container")) {
			$("body").append('<div id="notif-popup-container"></div>');
		}
	}

	function escapeHtml(value) {
		return String(value || "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
	}

	function getShownList() {
		try {
			return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
		} catch (e) {
			return [];
		}
	}

	function isAlreadyShown(id) {
		return getShownList().includes(id);
	}

	function markAsShown(id) {
		const shown = getShownList();
		if (!shown.includes(id)) {
			shown.push(id);
			if (shown.length > 200) shown.splice(0, shown.length - 200);
			localStorage.setItem(STORAGE_KEY, JSON.stringify(shown));
		}
	}

	function showToast(notif) {
		if (!notif || !notif.name || isAlreadyShown(notif.name)) return;

		const subject = escapeHtml(notif.subject || "New Notification");
		const body = escapeHtml(notif.email_content || "");

		const toast = $(`
            <div class="notif-toast" data-id="${notif.name}">
                <div class="notif-toast-body">
                    <div class="notif-toast-title">Notification</div>
                    <div class="notif-toast-message">${subject}${body ? "<br>" + body : ""}</div>
                </div>
                <span class="notif-toast-close">x</span>
            </div>
        `);

		toast.on("click", function (e) {
			if (!$(e.target).hasClass("notif-toast-close")) {
				if (notif.document_type && notif.document_name) {
					frappe.set_route("Form", notif.document_type, notif.document_name);
				}
				toast.remove();
			}
		});

		toast.find(".notif-toast-close").on("click", function () {
			toast.fadeOut(250, () => toast.remove());
		});

		$("#notif-popup-container").prepend(toast);
		markAsShown(notif.name);

		setTimeout(() => {
			toast.fadeOut(300, () => toast.remove());
		}, 3000);
	}

	function renderUnshown(rows, stagger) {
		const items = (rows || []).filter((n) => n && n.name && !isAlreadyShown(n.name)).reverse();
		items.forEach((notif, i) => {
			if (stagger) {
				setTimeout(() => showToast(notif), i * 300);
			} else {
				showToast(notif);
			}
		});
	}

	function fetchAndShow(limit = 10, stagger = false) {
		frappe.call({
			method: "frappe.desk.doctype.notification_log.notification_log.get_notification_logs",
			args: { limit },
			callback(r) {
				const rows = (r && r.message && r.message.notification_logs) || [];
				renderUnshown(rows, stagger);
			},
			error() {
				// fallback for any permission/routing issue
				frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Notification Log",
						filters: { for_user: frappe.session.user },
						fields: [
							"name",
							"subject",
							"email_content",
							"document_type",
							"document_name",
							"creation",
							"read",
						],
						order_by: "creation desc",
						limit_page_length: limit,
					},
					callback(rr) {
						const rows = (rr && rr.message) || [];
						renderUnshown(rows, stagger);
					},
				});
			},
		});
	}

	ensureContainer();
	fetchAndShow(15, true);
	setInterval(() => fetchAndShow(5, false), 8000);

	document.addEventListener("visibilitychange", function () {
		if (!document.hidden) fetchAndShow(10, false);
	});

	window.addEventListener("focus", function () {
		fetchAndShow(10, false);
	});

	// realtime push from Notification Log after_insert
	frappe.realtime.on("notification", function () {
		setTimeout(() => fetchAndShow(5, false), 600);
	});
}

$(document).ready(initFinNotificationPopup);
if (frappe.after_ajax) {
	frappe.after_ajax(initFinNotificationPopup);
}

// -----------------------------------------------
// FILE: your_app/public/js/custom.js
// PURPOSE: Customize Frappe Home Page UI behavior
// APPLY IN: hooks.py → app_include_js
// -----------------------------------------------

function initHomeCustomizations() {
	const route = (frappe.get_route_str && frappe.get_route_str()) || "";
	const isHomeRoute =
		route === "" || route === "home" || window.location.pathname === "/app/home";
	document.body.classList.toggle("fin-home-page", isHomeRoute);

	// ── 1. Rename a sidebar menu label ──
	// Find sidebar item by its text and rename it
	$(".standard-sidebar-item").each(function () {
		let link = $(this).find("a .item-name");
		if (link.text().trim() === "Sample") {
			link.text("My Custom Module");
		}
	});

	// ── 2. Hide specific sidebar items by name ──
	$(".standard-sidebar-item").each(function () {
		let text = $(this).find(".item-name").text().trim();
		if (["Build", "Sample"].includes(text)) {
			$(this).hide();
		}
	});

	// ── 3. Add a custom welcome banner on Home page ──
	if (isHomeRoute) {
		setTimeout(function () {
			if ($("#fin-home-welcome-banner").length) return;
			let banner = `
                <div id="fin-home-welcome-banner" style="
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 16px 24px;
                    border-radius: 10px;
                    margin-bottom: 16px;
                    font-size: 15px;
                ">
                    👋 Welcome back, ${frappe.session.user_fullname || "User"}!
                    Today is ${frappe.datetime.get_today()}.
                </div>
            `;
			$(".layout-main-section").prepend(banner);
		}, 500);
	}
}

$(document).ready(initHomeCustomizations);
if (frappe.after_ajax) {
	frappe.after_ajax(initHomeCustomizations);
}
if (frappe.router && frappe.router.on) {
	frappe.router.on("change", initHomeCustomizations);
}
