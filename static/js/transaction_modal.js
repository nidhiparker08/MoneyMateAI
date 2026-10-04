document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("transactionModal");

    if (!modal) return;

    const form = document.getElementById("transactionForm");

    const closeButtons = modal.querySelectorAll(
        ".modal-close, .cancel-btn"
    );

    function getCookie(name) {

        let cookieValue = null;

        if (document.cookie && document.cookie !== "") {

            const cookies = document.cookie.split(";");

            for (let cookie of cookies) {

                cookie = cookie.trim();

                if (cookie.startsWith(name + "=")) {

                    cookieValue = decodeURIComponent(
                        cookie.substring(name.length + 1)
                    );

                    break;

                }

            }

        }

        return cookieValue;

    }

    // ==========================================
    // OPEN MODAL
    // ==========================================

    function openModal() {

        form.dataset.action = "/transactions/create/";

        const submitButton = form.querySelector(".save-btn");

        submitButton.innerHTML =
            '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';

        modal.classList.add("active");

        document.body.style.overflow = "hidden";

    }

    // ==========================================
    // CLOSE MODAL
    // ==========================================

    function closeModal() {

        modal.classList.remove("active");

        document.body.style.overflow = "";

        form.reset();

        form.dataset.action = "/transactions/create/";

        const submitButton = form.querySelector(".save-btn");

        submitButton.innerHTML =
            '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';

    }

    // ==========================================
    // OPEN FROM SOURCE MODAL
    // ==========================================

    document.addEventListener(

        "openManualTransaction",

        function () {

            openModal();

        }

    );

    // ==========================================
    // CLOSE BUTTONS
    // ==========================================

    closeButtons.forEach(btn => {

        btn.addEventListener(

            "click",

            closeModal

        );

    });

    // ==========================================
    // CLICK OUTSIDE
    // ==========================================

    modal.addEventListener(

        "click",

        e => {

            if (e.target === modal) {

                closeModal();

            }

        }

    );

    // ==========================================
    // ESC
    // ==========================================

    document.addEventListener(

        "keydown",

        e => {

            if (e.key === "Escape") {

                closeModal();

            }

        }

    );

    // ==========================================
    // CLIENT-SIDE FUTURE DATE / TIME GUARD
    // ==========================================

    function hasFutureDateTime(form) {

        const dateInput   = form.querySelector("[name='transaction_date']");
        const timeInput   = form.querySelector("[name='transaction_time']");

        if (!dateInput || !dateInput.value) return null;

        const now = new Date();

        const pad = n => String(n).padStart(2, "0");

        const todayISO = [
            now.getFullYear(),
            pad(now.getMonth() + 1),
            pad(now.getDate()),
        ].join("-");

        if (dateInput.value > todayISO) {

            return "Transaction date cannot be in the future.";

        }

        if (
            dateInput.value === todayISO
            && timeInput
            && timeInput.value
        ) {

            const nowHHMM = [
                pad(now.getHours()),
                pad(now.getMinutes()),
            ].join(":");

            if (timeInput.value > nowHHMM) {

                return "Transaction time cannot be in the future.";

            }

        }

        return null;

    }

    // ==========================================
    // SUBMIT
    // ==========================================

    form.addEventListener(

        "submit",

        async function (e) {

            e.preventDefault();

            const submitButton =
                form.querySelector(".save-btn");

            submitButton.disabled = true;

            submitButton.innerHTML =
                '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

            const futureError = hasFutureDateTime(form);

            if (futureError) {

                submitButton.disabled = false;

                submitButton.innerHTML =
                    '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';

                FinToast(futureError, "error");

                return;

            }

            const formData =
                new FormData(form);

            try {

                const action =
                    form.dataset.action ||
                    "/transactions/create/";

                const response =
                    await fetch(action, {

                        method: "POST",

                        headers: {

                            "X-CSRFToken":
                                getCookie("csrftoken"),

                        },

                        body: formData,

                    });

                const data =
                    await response.json();

                if (data.success) {
                    console.log("SUCCESS RESPONSE");
                    console.log(data);

                    closeModal();
                    console.log("MODAL CLOSED");

                    FinToast(
                        "Transaction added successfully.",
                        "success"
                    );
                    console.log("TOAST SHOWN");
                    console.log("Reloading...");
                    location.reload();

                }

                else {

                    let message = data.message || "Failed to save transaction.";

                    // Surface the first form field error so the user knows
                    // exactly what to fix (e.g. future date/time).
                    if (data.errors) {

                        for (const field in data.errors) {

                            message = data.errors[field][0];

                            break;

                        }

                    }

                    FinToast(message, "error");

                    console.log(data.errors);

                }

            }

            catch (error) {

                FinToast(
                    "Something went wrong.",
                    "error"
                );

            }

            submitButton.disabled = false;

            submitButton.innerHTML =
                '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';

        }

    );

});