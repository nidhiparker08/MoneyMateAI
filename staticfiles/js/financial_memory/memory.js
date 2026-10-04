/* Financial Memory dashboard interactions. */
(function () {
    "use strict";

    function getCsrfToken() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : "";
    }

    function showToast(msg, type) {
        // FinSync ships a global toast — fallback to alert for safety.
        if (window.showToast) return window.showToast(msg, type);
        console.log("[toast]", type, msg);
    }

    async function postJSON(url) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken() },
            credentials: "same-origin",
        });
        return res.json();
    }

    // Re-scan recurring
    const btn = document.getElementById("detect-recurring-btn");
    if (btn) {
        btn.addEventListener("click", async () => {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning…';
            try {
                const data = await postJSON("/memory/detect-recurring/");
                if (data.success) {
                    showToast(data.message || "Recurring patterns updated.", "success");
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    showToast("Failed to re-scan.", "error");
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-wave-square"></i> Re-scan Recurring';
                }
            } catch (e) {
                showToast("Network error while re-scanning.", "error");
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-wave-square"></i> Re-scan Recurring';
            }
        });
    }

    // Toggle / delete memory entries via row actions.
    document.addEventListener("click", async (evt) => {
        const target = evt.target.closest("[data-action]");
        if (!target) return;
        const action = target.dataset.action;
        const id = target.dataset.id;
        if (!action || !id) return;

        if (action === "delete") {
            if (!confirm("Forget this memory permanently?")) return;
            const data = await postJSON(`/memory/entries/${id}/delete/`);
            if (data.success) {
                const row = document.getElementById(`entry-${id}`);
                row && row.remove();
                showToast("Memory forgotten.", "success");
            }
        } else if (action === "toggle") {
            const data = await postJSON(`/memory/entries/${id}/toggle/`);
            if (data.success) {
                const row = document.getElementById(`entry-${id}`);
                if (row) row.classList.toggle("entry-paused", !data.is_active);
                showToast(data.is_active ? "Memory activated." : "Memory paused.", "success");
            }
        }
    });
})();
