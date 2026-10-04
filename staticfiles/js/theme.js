/* ==========================================================
   FINSYNC AI  ·  THEME SYSTEM
   Handles Dark / Light / System with graceful sync between
   the OS preference, localStorage and the server-side profile.
   Exposed as window.FinSyncTheme.
========================================================== */
(function () {
    const STORAGE_KEY = "finsync-theme";
    const media = window.matchMedia("(prefers-color-scheme: light)");

    function resolveEffective(mode) {
        if (mode === "light" || mode === "dark") return mode;
        return media.matches ? "light" : "dark";
    }

    function applyTheme(mode) {
        const effective = resolveEffective(mode);
        document.documentElement.setAttribute("data-theme", effective);
        document.documentElement.setAttribute("data-theme-mode", mode);
        // Update the navbar moon/sun icon if present.
        const btn = document.querySelector(".theme-toggle-btn i");
        if (btn) {
            btn.className = effective === "light"
                ? "fa-solid fa-sun"
                : "fa-regular fa-moon";
        }
    }

    function get() {
        return localStorage.getItem(STORAGE_KEY) || "dark";
    }

    function set(mode) {
        localStorage.setItem(STORAGE_KEY, mode);
        applyTheme(mode);
    }

    function cycle() {
        const order = ["dark", "light", "system"];
        const next = order[(order.indexOf(get()) + 1) % order.length];
        set(next);
        return next;
    }

    // Re-apply theme when OS preference changes if we're in "system" mode.
    media.addEventListener("change", () => {
        if (get() === "system") applyTheme("system");
    });

    // Boot ASAP to avoid FOUC.
    applyTheme(get());

    window.FinSyncTheme = { get, set, cycle, apply: applyTheme };
})();
