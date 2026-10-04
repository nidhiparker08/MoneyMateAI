document.addEventListener("DOMContentLoaded", () => {

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

    // ===============================================
    // EDIT TRANSACTION
    // ===============================================

    document.querySelectorAll(".edit-btn").forEach(button => {

        button.addEventListener("click", async function() {

            const id = this.dataset.id;

            try {

                const response = await fetch(`/transactions/${id}/`);

                const data = await response.json();

                if (!data.success) {

                showToast(
                        data.message,
                        "error",
                        "Error"
                    );

                    return;

                }

                const t = data.transaction;

                const form = document.getElementById("transactionForm");

                form.dataset.action = `/transactions/update/${id}/`;

                console.log("Edit Mode Action:", form.dataset.action);

                form.querySelector("[name='title']").value = t.title;

                form.querySelector("[name='merchant']").value = t.merchant;

                form.querySelector("[name='amount']").value = t.amount;

                form.querySelector("[name='transaction_type']").value = t.transaction_type;

                form.querySelector("[name='category']").value = t.category;

                form.querySelector("[name='payment_method']").value = t.payment_method;

                form.querySelector("[name='transaction_date']").value = t.transaction_date;

                form.querySelector("[name='transaction_time']").value = t.transaction_time;

                form.querySelector("[name='notes']").value = t.notes;

                const submitButton = form.querySelector(".save-btn");

                submitButton.innerHTML =
                    '<i class="fa-solid fa-pen"></i> Update Transaction';

                document
                    .getElementById("transactionModal")
                    .classList
                    .add("active");

                document.body.style.overflow = "hidden";

            }

            catch (error) {

                console.error(error);

                showToast(
                    "Unable to load transaction.",
                    "error",
                    "Error"
                );

            }

        });

    });

    document.querySelectorAll(".delete-btn").forEach(button => {

        button.addEventListener("click", async function() {

            const id = this.dataset.id;

            const card = this.closest(".transaction-card");

            const confirmed = confirmAction(
                "Delete this transaction?",
                "Delete Transaction"
            );

            if (!confirmed) return;

            try {

                const response = await fetch(

                    `/transactions/delete/${id}/`,

                    {

                        method: "POST",

                        headers: {

                            "X-CSRFToken": getCookie("csrftoken")

                        }

                    }

                );

                const data = await response.json();

                if (data.success) {

                    card.style.transition = ".3s";

                    card.style.opacity = "0";

                    card.style.transform = "translateX(50px)";

                    setTimeout(() => {

                        card.remove();

                        location.reload();

                    }, 300);

                }

                else {

                    showToast(
                        data.message,
                        "error",
                        "Error"
                    );

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

        });

    });

    // ===============================================
    // AUTO SUBMIT FILTERS
    // ===============================================

    const filterForm = document.getElementById("filterForm");

    if (filterForm) {

        const searchInput = document.getElementById("searchInput");

        let timer;

        if (searchInput) {

            searchInput.addEventListener("input", function() {

                clearTimeout(timer);

                timer = setTimeout(() => {

                    filterForm.submit();

                }, 500);

            });

        }

        filterForm.querySelectorAll("select").forEach(select => {

            select.addEventListener("change", () => {

                filterForm.submit();

            });

        });

    }

});