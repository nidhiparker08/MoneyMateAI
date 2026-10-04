/* Notifications page — filter tabs, mark-read, dismiss, categorise */
(function () {
    const csrftoken = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="))?.split("=")[1];

    // ---- Filter tabs
    const filterBtns = document.querySelectorAll(".notif-filter");
    filterBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            filterBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            const filter = btn.dataset.filter;
            document.querySelectorAll(".notif-row").forEach((row) => {
                let show = true;
                if (filter === "unread") show = row.dataset.read === "0";
                else if (filter !== "all") show = row.dataset.category === filter;
                row.style.display = show ? "" : "none";
            });
        });
    });

    async function post(url) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": csrftoken || "" },
            credentials: "same-origin",
        });
        return res.json();
    }

    // ---- Delegate mark-read
    document.addEventListener("click", async (e) => {
        const readBtn = e.target.closest(".notif-mark-read");
        const dismBtn = e.target.closest(".notif-dismiss");
        const row = e.target.closest(".notif-row");
        if (!row) return;
        const id = row.dataset.notifId;

        if (readBtn) {
            const body = new URLSearchParams();
            body.append("id", id);
            await fetch("/notifications/api/mark-read/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrftoken || "",
                },
                body,
                credentials: "same-origin",
            });
            row.classList.remove("notif-unread");
            row.dataset.read = "1";
            readBtn.remove();
            if (window.FinToast) window.FinToast("Marked as read", "success");
        }
        if (dismBtn) {
            const j = await post(`/notifications/api/${id}/dismiss/`);
            if (j.success) row.remove();
        }
    });

    // ---- Bulk actions
    const markAll = document.getElementById("mark-all-read-btn");
    if (markAll) {
        markAll.addEventListener("click", async () => {
            const j = await post("/notifications/api/mark-all-read/");
            if (j.success) {
                document.querySelectorAll(".notif-unread").forEach((r) => {
                    r.classList.remove("notif-unread");
                    r.dataset.read = "1";
                });
                document.querySelectorAll(".notif-mark-read").forEach((b) => b.remove());
                if (window.FinToast) window.FinToast("All caught up", "success");
            }
        });
    }
    const clearAll = document.getElementById("clear-all-btn");
    if (clearAll) {
        clearAll.addEventListener("click", async () => {
            if (!confirm("Delete all notifications? This cannot be undone.")) return;
            const j = await post("/notifications/api/clear-all/");
            if (j.success) location.reload();
        });
    }
})();
