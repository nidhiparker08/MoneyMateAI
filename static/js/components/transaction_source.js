document.addEventListener("DOMContentLoaded", () => {

    const sourceModal = document.getElementById("transactionSourceModal");

    if (!sourceModal) return;

    // ==============================
    // BUTTONS
    // ==============================

    const addButtons        = document.querySelectorAll(".open-transaction-modal");
    const closeButton       = sourceModal.querySelector(".source-close");
    const manualButton      = document.getElementById("manualTransactionBtn");
    const connectBankButton = document.getElementById("connectBankBtn");

    // ==============================
    // OPEN / CLOSE
    // ==============================

    function openSourceModal() {
        sourceModal.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeSourceModal() {
        sourceModal.classList.remove("active");
        document.body.style.overflow = "";
    }

    addButtons.forEach(button => button.addEventListener("click", openSourceModal));

    if (closeButton) closeButton.addEventListener("click", closeSourceModal);

    sourceModal.addEventListener("click", e => {
        if (e.target === sourceModal) closeSourceModal();
    });

    document.addEventListener("keydown", e => {
        if (e.key === "Escape") closeSourceModal();
    });

    // ==============================
    // MANUAL TRANSACTION
    // ==============================

    if (manualButton) {
        manualButton.addEventListener("click", () => {
            closeSourceModal();
            document.dispatchEvent(new CustomEvent("openManualTransaction"));
        });
    }

    // ==============================
    // CONNECT BANK
    // ==============================

    if (connectBankButton) {
        connectBankButton.addEventListener("click", () => {
            closeSourceModal();
            const modal = document.getElementById("connectBankModal");
            if (modal) modal.classList.add("active");
        });
    }

});
