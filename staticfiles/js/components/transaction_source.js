document.addEventListener("DOMContentLoaded", () => {

    const sourceModal =
        document.getElementById("transactionSourceModal");

    if (!sourceModal) return;

    // ==============================
    // BUTTONS
    // ==============================

    const addButtons =
        document.querySelectorAll(".open-transaction-modal");

    const closeButton =
        sourceModal.querySelector(".source-close");

    const manualButton =
        document.getElementById("manualTransactionBtn");

    const statementButton =
        document.getElementById("statementImportBtn");

    const gmailButton =
        document.getElementById("gmailSyncBtn");

    // ==============================
    // OPEN SOURCE MODAL
    // ==============================

    function openSourceModal() {

        sourceModal.classList.add("active");

        document.body.style.overflow = "hidden";

    }

    // ==============================
    // CLOSE SOURCE MODAL
    // ==============================

    function closeSourceModal() {

        sourceModal.classList.remove("active");

        document.body.style.overflow = "";

    }

    // ==============================
    // OPEN BUTTONS
    // ==============================

    addButtons.forEach(button => {

        button.addEventListener(

            "click",

            openSourceModal

        );

    });

    // ==============================
    // CLOSE BUTTON
    // ==============================

    closeButton.addEventListener(

        "click",

        closeSourceModal

    );

    // ==============================
    // CLICK OUTSIDE
    // ==============================

    sourceModal.addEventListener(

        "click",

        e => {

            if (e.target === sourceModal) {

                closeSourceModal();

            }

        }

    );

    // ==============================
    // ESC KEY
    // ==============================

    document.addEventListener(

        "keydown",

        e => {

            if (e.key === "Escape") {

                closeSourceModal();

            }

        }

    );

    // ==============================
    // MANUAL TRANSACTION
    // ==============================

    manualButton.addEventListener(

        "click",

        () => {

            closeSourceModal();

            document.dispatchEvent(

                new CustomEvent(

                    "openManualTransaction"

                )

            );

        }

    );

    // ==============================
    // IMPORT STATEMENT
    // ==============================

    statementButton.addEventListener(

        "click",

        () => {

            window.location.href =
                "/transactions/import/";

        }

    );

    // ==============================
    // GMAIL SYNC
    // ==============================

    gmailButton.addEventListener(

        "click",

        () => {

            window.location.href =
                "/gmail/connect/";

        }

    );

});