/* ==========================================================
   MONEYMATE · EMAIL OTP VERIFICATION
   Six-box input behaviour, fetch verify/resend, countdown.
   Follows the existing CSRF conventions (settings.js).
   ========================================================== */
(function () {
    const form = document.getElementById("otpForm");
    if (!form) return;

    const inputs = Array.from(document.querySelectorAll(".mm-otp-input"));
    const submitBtn = document.getElementById("otpSubmit");
    const submitLabel = submitBtn.querySelector(".mm-otp-btn-label");
    const statusChip = document.getElementById("otpStatusChip");
    const resendBtn = document.getElementById("otpResend");
    const countdownEl = document.getElementById("otpCountdown");
    const alertBox = document.getElementById("otpAlert");
    const alertIcon = alertBox.querySelector("i");
    const alertText = document.getElementById("otpAlertText");

    const VERIFY_URL = form.action;
    const RESEND_URL = form.dataset.resendUrl;
    const REDIRECT_URL = form.dataset.redirect;
    const csrftoken = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="))?.split("=")[1];

    let countdown = parseInt(form.dataset.resendIn || "0", 10);
    let timer = null;
    let verified = false;

    // ---------- Alerts ----------
    function showAlert(message, type) { // "error" | "success"
        alertText.textContent = message;
        alertBox.classList.remove("mm-hidden", "mm-auth-alert-success");
        if (type === "error") {
            alertIcon.className = "fa-solid fa-circle-exclamation";
        } else {
            alertIcon.className = "fa-solid fa-circle-check";
            alertBox.classList.add("mm-auth-alert-success");
        }
    }
    function hideAlert() { alertBox.classList.add("mm-hidden"); }

    // ---------- Helpers ----------
    function getCode() { return inputs.map((i) => i.value).join(""); }
    function resetInputs() {
        inputs.forEach((i) => { i.value = ""; i.classList.remove("filled"); });
        inputs[0].focus();
    }
    function setLoading(loading, label, isSuccess) {
        submitBtn.classList.toggle("is-loading", loading);
        submitBtn.classList.toggle("is-success", !!isSuccess);
        submitBtn.disabled = loading || !!isSuccess;
        submitLabel.innerHTML = label;
    }
    function markVerified() {
        if (statusChip) {
            statusChip.innerHTML = '<i class="fa-solid fa-circle-check"></i> Verified';
            statusChip.classList.add("is-done");
        }
    }
    function shake() {
        const wrap = document.querySelector(".mm-otp-inputs");
        wrap.classList.remove("shake");
        void wrap.offsetWidth;
        wrap.classList.add("shake");
    }

    async function postJSON(url, body) {
        const opts = {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrftoken || "",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        };
        if (body !== undefined) {
            opts.headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(body);
        }
        return fetch(url, opts);
    }

    // ---------- Verify ----------
    async function submitCode() {
        if (verified) return;
        const code = getCode();
        if (code.length !== inputs.length) return;
        setLoading(true, '<i class="fa-solid fa-spinner fa-spin"></i> Verifying…');
        hideAlert();
        try {
            const res = await postJSON(VERIFY_URL, { otp: code });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.success) {
                verified = true;
                markVerified();
                setLoading(true, '<i class="fa-solid fa-check"></i> Verified', true);
                showAlert(data.message || "Email verified!", "success");
                setTimeout(() => {
                    window.location.href = data.redirect || REDIRECT_URL;
                }, 700);
                return;
            }
            setLoading(false, "Verify &amp; continue");
            shake();
            resetInputs();
            if (data.status === "locked" || data.status === "expired") {
                startCountdown(0); // allow an immediate resend
            }
            showAlert(data.message || "Verification failed. Please try again.", "error");
        } catch (err) {
            setLoading(false, "Verify &amp; continue");
            showAlert("Network error — please check your connection and try again.", "error");
        }
    }

    // ---------- Six-box input behaviour ----------
    inputs.forEach((input, index) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "").slice(-1);
            input.classList.toggle("filled", !!input.value);
            if (input.value && index < inputs.length - 1) inputs[index + 1].focus();
            if (inputs.every((i) => i.value)) submitCode();
        });
        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !input.value && index > 0) {
                e.preventDefault();
                inputs[index - 1].value = "";
                inputs[index - 1].classList.remove("filled");
                inputs[index - 1].focus();
            }
        });
        input.addEventListener("paste", (e) => {
            e.preventDefault();
            const digits = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, inputs.length);
            digits.split("").forEach((d, i) => {
                inputs[i].value = d;
                inputs[i].classList.add("filled");
            });
            inputs[Math.min(digits.length, inputs.length - 1)].focus();
            if (digits.length === inputs.length) submitCode();
        });
    });

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        submitCode();
    });

    // ---------- Resend countdown ----------
    function updateCountdown() {
        if (countdown > 0) {
            resendBtn.disabled = true;
            countdownEl.textContent = "in " + countdown + "s";
        } else {
            resendBtn.disabled = false;
            countdownEl.textContent = "";
        }
    }
    function startCountdown(seconds) {
        countdown = seconds;
        clearInterval(timer);
        updateCountdown();
        if (countdown <= 0) return;
        timer = setInterval(() => {
            countdown -= 1;
            updateCountdown();
            if (countdown <= 0) clearInterval(timer);
        }, 1000);
    }

    resendBtn.addEventListener("click", async () => {
        resendBtn.disabled = true;
        try {
            const res = await postJSON(RESEND_URL);
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.success) {
                let msg = data.message || "A new code is on its way.";
                if (data.dev_code) msg += " (Dev code: " + data.dev_code + ")";
                showAlert(msg, "success");
                resetInputs();
                startCountdown(data.resend_in || 60);
            } else {
                showAlert(data.message || "Couldn't resend the code. Please try again.", "error");
                startCountdown(data.resend_in || 0);
            }
        } catch (err) {
            showAlert("Network error — please try again.", "error");
            resendBtn.disabled = false;
        }
    });

    startCountdown(countdown);
})();

