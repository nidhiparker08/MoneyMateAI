/* Settings page — tab switching + AJAX persistence for every control */
(function () {
    const csrftoken = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="))?.split("=")[1];

    // ---- Tabs
    const tabs = document.querySelectorAll(".settings-tab");
    const panels = document.querySelectorAll(".settings-panel");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            panels.forEach((p) => p.classList.remove("active"));
            tab.classList.add("active");
            const target = document.querySelector(`.settings-panel[data-panel="${tab.dataset.tab}"]`);
            if (target) target.classList.add("active");
        });
    });

    // ---- POST helper
    async function updateSetting(key, value) {
        const body = new URLSearchParams();
        body.append(key, value);
        try {
            const res = await fetch("/accounts/settings/update/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrftoken || "",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body,
                credentials: "same-origin",
            });
            const j = await res.json();
            if (j.success && window.FinToast) {
                window.FinToast("Saved", "success");
            }
            return j;
        } catch (e) {
            if (window.FinToast) window.FinToast("Save failed", "error");
        }
    }

    // ---- Select / text inputs
    document.querySelectorAll("[data-setting]").forEach((el) => {
        if (el.type === "checkbox") {
            el.addEventListener("change", () =>
                updateSetting(el.dataset.setting, el.checked ? "true" : "false")
            );
        } else {
            el.addEventListener("change", () =>
                updateSetting(el.dataset.setting, el.value)
            );
        }
    });

    // ---- Theme picker
    const themeButtons = document.querySelectorAll(".theme-option");
    themeButtons.forEach((btn) => {
        btn.addEventListener("click", async () => {
            const val = btn.dataset.themeValue;
            themeButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            if (window.FinSyncTheme) window.FinSyncTheme.set(val);
            await updateSetting("theme", val);
        });
    });
})();
