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

                    closeModal();

                    showToast(

                        "Transaction added successfully.",

                        "success",

                        "Success"

                    );

                    location.reload();

                }

                else {

                    showToast(

                        "Failed to save transaction.",

                        "error",

                        "Error"

                    );

                    console.log(data.errors);

                }

            }

            catch (error) {

                console.error(error);

                    showToast(

                    "Something went wrong.",

                    "error",

                    "Error"

                );

            }

            submitButton.disabled = false;

            submitButton.innerHTML =
                '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';

        }

    );

});