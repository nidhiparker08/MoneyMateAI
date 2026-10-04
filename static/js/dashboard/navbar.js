/* ==========================================================
   NAVBAR — bell dropdown, theme toggle, profile dropdown
========================================================== */
(function () {
    const csrftoken = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="))?.split("=")[1];

    // ---------- THEME TOGGLE ----------
    const themeBtn = document.querySelector(".theme-toggle-btn");
    if (themeBtn && window.FinSyncTheme) {
        themeBtn.addEventListener("click", () => {
            const mode = window.FinSyncTheme.cycle();
            if (window.FinToast) window.FinToast(`Theme: ${mode}`, "info");
        });
    }

    // ---------- PROFILE DROPDOWN ----------
    const profileTrigger = document.querySelector("[data-testid='profile-menu-trigger']");
    const profileMenu = document.querySelector("[data-testid='profile-dropdown']");
    if (profileTrigger && profileMenu) {
        profileTrigger.addEventListener("click", (e) => {
            e.stopPropagation();
            profileMenu.classList.toggle("open");
        });
    }

    // ---------- NOTIFICATIONS DROPDOWN ----------
    const bell = document.querySelector(".notification-btn");
    const dropdown = document.querySelector(".notif-dropdown");
    const badge = document.querySelector(".notification-badge");
    const list = document.querySelector(".notif-dd-list");

    async function loadNotifications() {
        try {
            const res = await fetch("/notifications/api/list/?limit=8", { credentials: "same-origin" });
            const j = await res.json();
            renderBadge(j.unread_count);
            renderList(j.notifications);
        } catch {}
    }

    function renderBadge(count) {
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? "99+" : count;
            badge.classList.add("show");
        } else {
            badge.textContent = "";
            badge.classList.remove("show");
        }
    }

    function renderList(items) {
        if (!list) return;
        if (!items.length) {
            list.innerHTML = '<div class="notif-dd-empty"><i class="fa-regular fa-bell-slash"></i><p>No notifications yet</p></div>';
            return;
        }
        list.innerHTML = items.map(n => `
            <a href="${n.action_url || '/notifications/'}"
               class="notif-dd-item ${n.is_read ? '' : 'unread'}"
               data-id="${n.id}">
                <div class="notif-dd-icon"><i class="fa-solid ${n.icon}"></i></div>
                <div class="notif-dd-body">
                    <strong>${escapeHtml(n.title)}</strong>
                    <p>${escapeHtml(n.description)}</p>
                    <span class="time">${timeAgo(n.created_at)}</span>
                </div>
            </a>
        `).join("");
    }

    function escapeHtml(s) {
        return String(s || "").replace(/[&<>"']/g, (m) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
        }[m]));
    }

    function timeAgo(iso) {
        try {
            const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
            if (s < 60) return "just now";
            if (s < 3600) return `${Math.floor(s / 60)}m ago`;
            if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
            return `${Math.floor(s / 86400)}d ago`;
        } catch { return ""; }
    }

    if (bell && dropdown) {
        bell.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = dropdown.classList.toggle("open");
            if (isOpen) loadNotifications();
            if (profileMenu) profileMenu.classList.remove("open");
        });
    }

    // Close menus on outside click
    document.addEventListener("click", (e) => {
        if (dropdown && !dropdown.contains(e.target) && !bell?.contains(e.target)) {
            dropdown.classList.remove("open");
        }
        if (profileMenu && !profileMenu.contains(e.target) && !profileTrigger?.contains(e.target)) {
            profileMenu.classList.remove("open");
        }
    });

    // "Mark all read" inside dropdown
    document.addEventListener("click", async (e) => {
        if (e.target.matches("[data-testid='dd-mark-all-read']")) {
            e.preventDefault();
            await fetch("/notifications/api/mark-all-read/", {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken || "" },
                credentials: "same-origin",
            });
            loadNotifications();
        }
    });

    // Poll every 45s so the badge stays fresh
    setInterval(() => {
        if (document.hidden) return;
        fetch("/notifications/api/unread-count/", { credentials: "same-origin" })
            .then(r => r.json())
            .then(j => renderBadge(j.unread_count))
            .catch(() => {});
    }, 45000);

    // Initial badge fetch
    loadNotifications();
})();
