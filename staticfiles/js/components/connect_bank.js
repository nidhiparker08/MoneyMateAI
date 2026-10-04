/* ==========================================================
   CONNECT BANK — Premium Flow (BankHub)
   • No alerts / no debug logging
   • Sequential loading messages driven while the API is in flight
   • Success screen with dynamic bank + counts, auto-refresh
   • Modal locked during the request
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    // ---------------------------------------------------------
    // Elements
    // ---------------------------------------------------------
    const connectBankModal = document.getElementById("connectBankModal");
    const bankAuthModal    = document.getElementById("bankAuthModal");

    if (!connectBankModal || !bankAuthModal) return;

    const bankOptions      = connectBankModal.querySelectorAll(".bank-option");
    const bankContinueBtn  = document.getElementById("bankContinueBtn");
    const closeBankModal   = document.getElementById("closeBankModal");

    const bankAuthForm      = document.getElementById("bankAuthForm");
    const closeAuthBtn      = document.getElementById("closeBankAuthModal");
    const submitBtn         = document.getElementById("connectBankSubmit");

    const formContainer     = document.getElementById("bankAuthFormContainer");
    const loadingContainer  = document.getElementById("bankLoadingContainer");
    const successContainer  = document.getElementById("bankSuccessContainer");

    const loadingStatusEl   = document.getElementById("bankLoadingStatus");
    const progressFillEl    = document.getElementById("bankProgressFill");
    const stepListEl        = document.getElementById("bankLoadingSteps");

    const successBankEl     = document.getElementById("bankSuccessBank");
    const successTxCountEl  = document.getElementById("bankSuccessTxCount");
    const successInvCountEl = document.getElementById("bankSuccessInvCount");

    let selectedBank      = null;
    let selectedBankName  = null;
    let isSubmitting      = false;

    // ---------------------------------------------------------
    // Loading step config (icon + label + progress %)
    // ---------------------------------------------------------
    const STEPS = [
        { key: "auth",         icon: "fa-key",              label: "Authenticating…",         progress: 15 },
        { key: "account",      icon: "fa-user-shield",      label: "Fetching Account…",       progress: 32 },
        { key: "transactions", icon: "fa-receipt",          label: "Importing Transactions…", progress: 55 },
        { key: "investments",  icon: "fa-chart-line",       label: "Importing Investments…",  progress: 72 },
        { key: "memory",       icon: "fa-brain",            label: "Teaching AI Memory…",     progress: 88 },
        { key: "finalize",     icon: "fa-circle-check",     label: "Finalizing…",             progress: 100 }
    ];

    // ---------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------
    function getCsrfToken() {
        const el = document.querySelector("[name=csrfmiddlewaretoken]");
        return el ? el.value : "";
    }

    function resetSelection() {
        selectedBank     = null;
        selectedBankName = null;
        bankOptions.forEach(b => b.classList.remove("selected"));
        if (bankContinueBtn) bankContinueBtn.disabled = true;
    }

    function resetAuthForm() {
        if (bankAuthForm) bankAuthForm.reset();
    }

    function openConnectModal() {
        connectBankModal.classList.add("active");
    }

    function closeConnectModal() {
        connectBankModal.classList.remove("active");
    }

    function openAuthModal() {
        // ensure default panel is visible
        showFormPanel();
        bankAuthModal.classList.add("active");
        // focus first field for premium feel
        setTimeout(() => {
            const first = document.getElementById("bankUserName");
            if (first) first.focus();
        }, 260);
    }

    function closeAuthModal() {
        if (isSubmitting) return;                // hard-lock while submitting
        bankAuthModal.classList.remove("active");
        // give the close animation a moment before resetting panels
        setTimeout(() => {
            showFormPanel();
            resetAuthForm();
        }, 260);
    }

    function showFormPanel() {
        if (formContainer)    formContainer.style.display    = "";
        if (loadingContainer) loadingContainer.style.display = "none";
        if (successContainer) successContainer.style.display = "none";
    }

    function showLoadingPanel() {
        if (formContainer)    formContainer.style.display    = "none";
        if (loadingContainer) loadingContainer.style.display = "";
        if (successContainer) successContainer.style.display = "none";
    }

    function showSuccessPanel() {
        if (formContainer)    formContainer.style.display    = "none";
        if (loadingContainer) loadingContainer.style.display = "none";
        if (successContainer) successContainer.style.display = "";
    }

    // ---------------------------------------------------------
    // Loading orchestration
    // ---------------------------------------------------------
    function setStep(index, { markPreviousDone = true } = {}) {
        const step = STEPS[index];
        if (!step) return;

        // update visible message with a soft fade
        if (loadingStatusEl) {
            loadingStatusEl.classList.add("fade");
            setTimeout(() => {
                loadingStatusEl.innerHTML =
                    `<i class="fa-solid ${step.icon}"></i>${step.label}`;
                loadingStatusEl.classList.remove("fade");
            }, 180);
        }

        // progress bar
        if (progressFillEl) {
            progressFillEl.style.width = step.progress + "%";
        }

        // step list
        if (stepListEl) {
            const items = stepListEl.querySelectorAll("li");
            items.forEach((li, i) => {
                li.classList.remove("active", "done");
                if (i < index && markPreviousDone) {
                    li.classList.add("done");
                } else if (i === index) {
                    li.classList.add("active");
                }
            });
        }
    }

    function completeAllSteps() {
        if (progressFillEl) progressFillEl.style.width = "100%";
        if (stepListEl) {
            stepListEl.querySelectorAll("li").forEach(li => {
                li.classList.remove("active");
                li.classList.add("done");
            });
        }
    }

    // Sequentially cycles through steps 0..4 while the network request is in flight.
    // Returns a controller that can be used to jump to the final step & stop the loop.
    function startLoadingSequence() {
        let currentIndex = 0;
        setStep(currentIndex);

        // Cycle through the first 5 messages (auth → memory) at a comfortable pace.
        // Step 5 (finalize) is reserved to run once the API responds.
        const intervalMs = 700;
        let stopped = false;

        const timer = setInterval(() => {
            if (stopped) return;
            if (currentIndex < STEPS.length - 2) {
                currentIndex += 1;
                setStep(currentIndex);
            }
        }, intervalMs);

        return {
            finish() {
                stopped = true;
                clearInterval(timer);
                // Jump to Finalizing then complete
                setStep(STEPS.length - 1);
                setTimeout(completeAllSteps, 220);
            },
            fail() {
                stopped = true;
                clearInterval(timer);
            }
        };
    }

    // ---------------------------------------------------------
    // BANK SELECTION
    // ---------------------------------------------------------
    bankOptions.forEach(btn => {
        btn.addEventListener("click", () => {
            bankOptions.forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            selectedBank     = btn.dataset.bank;
            selectedBankName = btn.dataset.bankName || btn.dataset.bank;
            if (bankContinueBtn) bankContinueBtn.disabled = false;
        });
    });

    if (bankContinueBtn) {
        bankContinueBtn.addEventListener("click", () => {
            if (!selectedBank) return;
            closeConnectModal();
            setTimeout(openAuthModal, 180);
        });
    }

    // ---------------------------------------------------------
    // CLOSE HANDLERS
    // ---------------------------------------------------------
    if (closeBankModal) {
        closeBankModal.addEventListener("click", () => {
            closeConnectModal();
            resetSelection();
        });
    }

    connectBankModal.addEventListener("click", (e) => {
        if (e.target === connectBankModal) {
            closeConnectModal();
            resetSelection();
        }
    });

    if (closeAuthBtn) {
        closeAuthBtn.addEventListener("click", closeAuthModal);
    }

    bankAuthModal.addEventListener("click", (e) => {
        if (e.target === bankAuthModal) closeAuthModal();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key !== "Escape") return;
        if (isSubmitting) return;
        if (bankAuthModal.classList.contains("active"))    closeAuthModal();
        if (connectBankModal.classList.contains("active")) closeConnectModal();
    });

    // ---------------------------------------------------------
    // SUBMIT — Connect Bank
    // ---------------------------------------------------------
    if (bankAuthForm) {

        bankAuthForm.addEventListener("submit", async (e) => {

            e.preventDefault();

            if (isSubmitting) return;   // prevent duplicate submissions
            isSubmitting = true;

            const nameEl  = document.getElementById("bankUserName");
            const emailEl = document.getElementById("bankEmail");
            const phoneEl = document.getElementById("bankPhone");

            const payload = {
                bank:  selectedBank,
                name:  nameEl  ? nameEl.value.trim()  : "",
                email: emailEl ? emailEl.value.trim() : "",
                phone: phoneEl ? phoneEl.value.trim() : ""
            };

            // Lock down the modal
            bankAuthModal.classList.add("locked");
            if (submitBtn) submitBtn.disabled = true;
            [nameEl, emailEl, phoneEl].forEach(i => { if (i) i.disabled = true; });

            // Switch to loading panel & start step sequence
            showLoadingPanel();
            const seq = startLoadingSequence();

            try {

                const response = await fetch("/transactions/connect-bank/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken()
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json().catch(() => ({}));

                if (response.ok && data && data.success) {

                    // Jump to Finalizing → complete
                    seq.finish();

                    // Populate success screen
                    const bankLabel = (data.bank || selectedBankName || selectedBank || "Bank").toString();
                    if (successBankEl) {
                        successBankEl.querySelector("span").textContent = bankLabel;
                    }
                    if (successTxCountEl) {
                        successTxCountEl.textContent = data.transactions_imported ?? 0;
                    }
                    if (successInvCountEl) {
                        successInvCountEl.textContent = data.investments_imported ?? 0;
                    }

                    // Small delay for the "Finalizing" beat, then reveal success
                    setTimeout(() => {
                        showSuccessPanel();
                        // Auto refresh the dashboard for the wow moment
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    }, 550);

                    return;
                }

                // -- Failure path -------------------------------------------------
                seq.fail();
                const errMessage = (data && data.error)
                    ? data.error
                    : "Failed to connect bank. Please try again.";

                if (typeof showToast === "function") {
                    showToast(errMessage, "error", "Connection Failed");
                }

                // Recover UI
                showFormPanel();
                bankAuthModal.classList.remove("locked");
                if (submitBtn) submitBtn.disabled = false;
                [nameEl, emailEl, phoneEl].forEach(i => { if (i) i.disabled = false; });
                isSubmitting = false;

            } catch (err) {

                seq.fail();

                if (typeof showToast === "function") {
                    showToast(
                        "Unable to reach BankHub. Please check your connection and try again.",
                        "error",
                        "Network Error"
                    );
                }

                // Recover UI
                showFormPanel();
                bankAuthModal.classList.remove("locked");
                if (submitBtn) submitBtn.disabled = false;
                [nameEl, emailEl, phoneEl].forEach(i => { if (i) i.disabled = false; });
                isSubmitting = false;
            }

        });

    }

});
