/* ==========================================================
   MONEYMATE · THEME SYSTEM
   Light / Dark / System with localStorage persistence,
   OS detection and smooth transitions. window.MoneyMateTheme.
========================================================== */
(function () {
    const STORAGE_KEY = "moneymate-theme";
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    function resolveEffective(mode) {
        if (mode === "light" || mode === "dark") return mode;
        return media.matches ? "dark" : "light";
    }

    function applyTheme(mode) {
        const effective = resolveEffective(mode);
        document.documentElement.setAttribute("data-theme", effective);
        document.documentElement.setAttribute("data-theme-mode", mode);
        document.querySelectorAll("[data-theme-icon], .theme-toggle-btn i").forEach((el) => {
            el.className = effective === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
        });
        window.dispatchEvent(new CustomEvent("mm-theme-change", { detail: { effective, mode } }));
    }

    function get() { return localStorage.getItem(STORAGE_KEY) || "light"; }

    function set(mode) {
        localStorage.setItem(STORAGE_KEY, mode);
        document.documentElement.classList.add("mm-theme-anim");
        applyTheme(mode);
        window.setTimeout(() => document.documentElement.classList.remove("mm-theme-anim"), 400);
    }

    function toggle() {
        const next = resolveEffective(get()) === "dark" ? "light" : "dark";
        set(next);
        return next;
    }

    function cycle() {
        const order = ["light", "dark", "system"];
        const next = order[(order.indexOf(get()) + 1) % order.length];
        set(next);
        return next;
    }

    media.addEventListener("change", () => { if (get() === "system") applyTheme("system"); });
    applyTheme(get());

    document.addEventListener("click", (e) => {
        const t = e.target.closest("[data-mm-theme-toggle]");
        if (t) { e.preventDefault(); toggle(); }
    });

    window.MoneyMateTheme = { get, set, toggle, cycle, apply: applyTheme };
    window.FinSyncTheme = window.MoneyMateTheme; // legacy alias
})();
