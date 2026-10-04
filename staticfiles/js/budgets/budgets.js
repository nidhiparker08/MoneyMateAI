document.addEventListener("DOMContentLoaded", function() {

    console.log("Budgets JS Loaded");

    const modal = document.getElementById("budgetModal");
    const form = document.getElementById("budgetForm");

    const addBtn = document.getElementById("addBudgetBtn");
    const createBtn = document.getElementById("createBudgetBtn");

    const closeBtn = document.getElementById("closeBudgetModal");
    const cancelBtn = document.getElementById("cancelBudget");

    if (!modal || !form) {
        console.error("Budget modal or form not found.");
        return;
    }

    const csrfInput = document.querySelector(
        "#budgetForm [name=csrfmiddlewaretoken]"
    );

    const csrfToken = csrfInput ? csrfInput.value : "";

    // ==========================================
    // OPEN MODAL
    // ==========================================

    function openModal() {
        modal.classList.add("show");
    }

    // ==========================================
    // CLOSE MODAL
    // ==========================================

    function closeModal() {

        modal.classList.remove("show");

        form.reset();

        const budgetId = document.getElementById("budgetId");
        const title = document.getElementById("budgetModalTitle");

        if (budgetId) budgetId.value = "";

        if (title) title.textContent = "Add Budget";
    }

    // ==========================================
    // BUTTON EVENTS
    // ==========================================

    if (addBtn) {
        addBtn.addEventListener("click", openModal);
    }

    if (createBtn) {
        createBtn.addEventListener("click", openModal);
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", closeModal);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener("click", closeModal);
    }

    // ==========================================
    // CLICK OUTSIDE
    // ==========================================

    modal.addEventListener("click", function(e) {

        if (e.target === modal) {

            closeModal();

        }

    });

    // ==========================================
    // EDIT
    // ==========================================

    document.querySelectorAll(".edit-budget").forEach(function(button) {

        button.addEventListener("click", function() {

            openModal();

            document.getElementById("budgetModalTitle").textContent =
                "Edit Budget";

            document.getElementById("budgetId").value =
                button.dataset.id;

            document.getElementById("budgetCategory").value =
                button.dataset.category;

            document.getElementById("budgetAmount").value =
                button.dataset.amount;

            document.getElementById("budgetMonth").value =
                button.dataset.month;

            document.getElementById("budgetYear").value =
                button.dataset.year;

        });

    });

    // ==========================================
    // DELETE
    // ==========================================

    document.querySelectorAll(".delete-budget").forEach(function(button) {

        button.addEventListener("click", async function() {

            if (!confirmAction("Delete this budget?", "Delete Budget")) {

                return;

            }

            try {

                const response = await fetch(

                    `/budgets/delete/${button.dataset.id}/`,

                    {

                        method: "POST",

                        headers: {

                            "X-CSRFToken": csrfToken

                        }

                    }

                );

                const data = await response.json();

                if (data.success) {

                    location.reload();

                } else {

                    showToast(data.message || "Delete failed.", "error", "Error");

                }

            } catch (err) {

                console.error(err);

            }

        });

    });

    // ==========================================
    // CREATE / UPDATE
    // ==========================================

    form.addEventListener("submit", async function(e) {

        e.preventDefault();

        const budgetId = document.getElementById("budgetId").value;

        const url = budgetId

            ? `/budgets/update/${budgetId}/`

            : `/budgets/create/`;

        try {

            const response = await fetch(url, {

                method: "POST",

                body: new FormData(form),

                headers: {

                    "X-CSRFToken": csrfToken

                }

            });

            const data = await response.json();

            if (data.success) {

                closeModal();

                location.reload();

            } else {

                showToast(data.message || "Unable to save budget.", "error", "Error");   

            }

        } catch (err) {

            console.error(err);

            showToast("Something went wrong.", "error", "Error");

        }

    });

});