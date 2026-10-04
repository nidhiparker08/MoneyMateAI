/* ==========================================================
   MONEYMATE · INTERACTIONS
   Loader, scroll reveal, count-up, FAQ, mobile nav,
   custom cursor (magnetic), subtle UI sounds + mute toggle,
   password reveal, hero chart draw.
========================================================== */
(function () {
    "use strict";
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isTouch = window.matchMedia("(hover: none), (pointer: coarse)").matches;

    /* ---------- Loader ---------- */
    function hideLoader() {
        const l = document.getElementById("loader");
        if (l) { l.classList.add("is-done"); setTimeout(() => (l.style.display = "none"), 500); }
    }
    window.addEventListener("load", () => setTimeout(hideLoader, 350));
    setTimeout(hideLoader, 2500);

    /* ---------- Scroll reveal ---------- */
    function initReveal() {
        const els = document.querySelectorAll(".reveal, [data-reveal]");
        if (!els.length) return;
        if (reduceMotion || !("IntersectionObserver" in window)) {
            els.forEach((e) => e.classList.add("is-in"));
            return;
        }
        const io = new IntersectionObserver((entries) => {
            entries.forEach((en, i) => {
                if (en.isIntersecting) {
                    setTimeout(() => en.target.classList.add("is-in"), (i % 6) * 60);
                    io.unobserve(en.target);
                }
            });
        }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
        els.forEach((e) => io.observe(e));
    }

    /* ---------- Count up ---------- */
    function initCounters() {
        const nums = document.querySelectorAll("[data-count]");
        if (!nums.length) return;
        const run = (el) => {
            const target = parseFloat(el.getAttribute("data-count"));
            const dec = (el.getAttribute("data-count").split(".")[1] || "").length;
            const prefix = el.getAttribute("data-prefix") || "";
            const suffix = el.getAttribute("data-suffix") || "";
            if (reduceMotion) { el.textContent = prefix + target.toLocaleString("en-IN") + suffix; return; }
            const dur = 1400; const start = performance.now();
            const step = (now) => {
                const p = Math.min((now - start) / dur, 1);
                const eased = 1 - Math.pow(1 - p, 3);
                const val = target * eased;
                el.textContent = prefix + (dec ? val.toFixed(dec) : Math.round(val).toLocaleString("en-IN")) + suffix;
                if (p < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        };
        const io = new IntersectionObserver((entries) => {
            entries.forEach((en) => { if (en.isIntersecting) { run(en.target); io.unobserve(en.target); } });
        }, { threshold: 0.4 });
        nums.forEach((n) => io.observe(n));
    }

    /* ---------- FAQ accordion ---------- */
    function initFaq() {
        document.querySelectorAll(".mm-faq-item").forEach((item) => {
            const q = item.querySelector(".mm-faq-q");
            if (!q) return;
            q.addEventListener("click", () => {
                const open = item.classList.contains("open");
                item.parentElement.querySelectorAll(".mm-faq-item.open").forEach((o) => o.classList.remove("open"));
                if (!open) item.classList.add("open");
                Sound.play("toggle");
            });
        });
    }

    /* ---------- Mobile nav ---------- */
    function initMobileNav() {
        const btn = document.querySelector("[data-mm-nav-toggle]");
        const nav = document.querySelector(".mm-nav");
        if (!btn || !nav) return;
        btn.addEventListener("click", () => nav.classList.toggle("open"));
        nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => nav.classList.remove("open")));
    }

    /* ---------- Password reveal ---------- */
    function initPasswordToggle() {
        document.querySelectorAll("[data-mm-eye]").forEach((eye) => {
            eye.addEventListener("click", () => {
                const input = eye.closest(".mm-field, .password-box, .input-group")?.querySelector("input[type='password'], input[type='text']");
                if (!input) return;
                const show = input.type === "password";
                input.type = show ? "text" : "password";
                eye.className = show ? "fa-solid fa-eye-slash mm-eye" : "fa-solid fa-eye mm-eye";
            });
        });
    }

    /* ---------- Custom cursor ---------- */
    function initCursor() {
        if (isTouch) return;
        const ring = document.querySelector(".mm-cursor");
        const dot = document.querySelector(".mm-cursor-dot");
        if (!ring || !dot) return;
        document.documentElement.classList.add("mm-has-cursor");
        let mx = window.innerWidth / 2, my = window.innerHeight / 2;
        let rx = mx, ry = my;
        window.addEventListener("mousemove", (e) => {
            mx = e.clientX; my = e.clientY;
            dot.style.transform = `translate(${mx}px, ${my}px)`;
        });
        const loop = () => { rx += (mx - rx) * 0.18; ry += (my - ry) * 0.18; ring.style.transform = `translate(${rx}px, ${ry}px)`; requestAnimationFrame(loop); };
        requestAnimationFrame(loop);
        const hoverSel = "a, button, .mm-btn, input, select, textarea, [role='button'], .menu-item, .mm-card-hover";
        document.addEventListener("mouseover", (e) => { if (e.target.closest(hoverSel)) ring.classList.add("is-hover"); });
        document.addEventListener("mouseout", (e) => { if (e.target.closest(hoverSel)) ring.classList.remove("is-hover"); });
    }

    /* ---------- Sound ---------- */
    const Sound = (function () {
        let enabled = localStorage.getItem("mm-sound") === "on";
        let ctx = null;
        const tones = { click: [520, 0.04], hover: [880, 0.02], success: [660, 0.09], toggle: [420, 0.05], notification: [740, 0.08] };
        function ensure() { if (!ctx) { try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} } }
        function play(name) {
            if (!enabled || reduceMotion) return;
            ensure(); if (!ctx) return;
            const [freq, vol] = tones[name] || tones.click;
            const o = ctx.createOscillator(); const g = ctx.createGain();
            o.type = "sine"; o.frequency.value = freq;
            g.gain.setValueAtTime(vol, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18);
            o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.2);
        }
        function setEnabled(v) { enabled = v; localStorage.setItem("mm-sound", v ? "on" : "off"); syncBtns(); }
        function syncBtns() {
            document.querySelectorAll("[data-mm-sound-toggle]").forEach((b) => {
                b.classList.toggle("is-on", enabled);
                const i = b.querySelector("i");
                if (i) i.className = enabled ? "fa-solid fa-volume-high" : "fa-solid fa-volume-xmark";
            });
        }
        return { play, setEnabled, isEnabled: () => enabled, syncBtns };
    })();
    window.MoneyMateSound = Sound;

    function initSound() {
        Sound.syncBtns();
        document.addEventListener("click", (e) => {
            const t = e.target.closest("[data-mm-sound-toggle]");
            if (t) { Sound.setEnabled(!Sound.isEnabled()); Sound.play("toggle"); return; }
            if (e.target.closest("a, button, .mm-btn, [role='button']")) Sound.play("click");
        });
    }

    /* ---------- Hero chart draw ---------- */
    function initHeroChart() {
        const path = document.querySelector("[data-mm-chart-line]");
        if (!path) return;
        try {
            const len = path.getTotalLength();
            path.style.strokeDasharray = len;
            path.style.strokeDashoffset = reduceMotion ? 0 : len;
            if (!reduceMotion) {
                requestAnimationFrame(() => { path.style.transition = "stroke-dashoffset 1.8s cubic-bezier(.4,0,.2,1)"; path.style.strokeDashoffset = 0; });
            }
        } catch (e) {}
    }

    function boot() {
        initReveal(); initCounters(); initFaq(); initMobileNav();
        initPasswordToggle(); initCursor(); initSound(); initHeroChart();
    }
    if (document.readyState !== "loading") boot();
    else document.addEventListener("DOMContentLoaded", boot);
})();
