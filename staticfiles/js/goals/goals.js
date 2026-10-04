/* ==========================================================
   FinSync AI - Goals Page
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    GoalModal.init();
    GoalFilters.init();
    GoalAnimations.init();
    GoalAI.init();
    GoalDelete.init();
    GoalContribution.init();

});


/* ==========================================================
   GOAL MODAL
========================================================== */

const GoalModal = {

    modal: null,
    form: null,

    init() {

        this.modal = document.getElementById("goal-modal");
        this.form = document.getElementById("goal-form");

        if (!this.modal) return;

        this.bindOpenButtons();
        this.bindCloseButtons();
        this.bindSubmit();

    },

    bindOpenButtons() {

        document.querySelectorAll("#add-goal-btn,#empty-add-goal").forEach(btn => {

            btn.addEventListener("click", () => this.open());

        });

    },

    bindCloseButtons() {

        document.getElementById("goal-modal-close")?.addEventListener("click", () => this.close());

        document.getElementById("goal-cancel-btn")?.addEventListener("click", () => this.close());

        this.modal.addEventListener("click", e => {

            if (e.target === this.modal) {

                this.close();

            }

        });

        document.addEventListener("keydown", e => {

            if (e.key === "Escape" && this.modal.classList.contains("show")) {

                this.close();

            }

        });

    },

    bindSubmit() {

        if (!this.form) return;

        this.form.addEventListener("submit", () => {

            const btn = this.form.querySelector(".goal-save-btn");

            btn.disabled = true;

            btn.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                Saving...
            `;

        });

    },

    open() {

        this.modal.classList.add("show");

        document.body.style.overflow = "hidden";

        setTimeout(() => {

            document.getElementById("goal-title")?.focus();

        }, 150);

    },

    close() {

        this.modal.classList.remove("show");

        document.body.style.overflow = "";

        this.form?.reset();

        const btn = this.form?.querySelector(".goal-save-btn");

        if (btn) {

            btn.disabled = false;

            btn.innerHTML = `
                <i class="fa-solid fa-floppy-disk"></i>
                Save Goal
            `;

        }

    }

};


/* ==========================================================
   FILTERS
========================================================== */

const GoalFilters = {

    init() {

        [
            "goal-search",
            "goal-type-filter",
            "priority-filter",
            "status-filter"
        ].forEach(id => {

            document.getElementById(id)?.addEventListener("input", () => this.filter());

            document.getElementById(id)?.addEventListener("change", () => this.filter());

        });

        document.getElementById("goal-reset-btn")
            ?.addEventListener("click", () => this.reset());

    },

    filter() {

        const search = document
            .getElementById("goal-search")
            ?.value
            .toLowerCase() || "";

        document.querySelectorAll(".goal-card").forEach(card => {

            const title = card.querySelector("h3")?.innerText.toLowerCase() || "";

            card.style.display = title.includes(search)
                ? ""
                : "none";

        });

    },

    reset() {

        document.getElementById("goal-search").value = "";

        document.getElementById("goal-type-filter").selectedIndex = 0;

        document.getElementById("priority-filter").selectedIndex = 0;

        document.getElementById("status-filter").selectedIndex = 0;

        this.filter();

    }

};


/* ==========================================================
   PROGRESS BAR ANIMATION
========================================================== */

const GoalAnimations = {

    init() {

        document.querySelectorAll(".goal-progress-fill").forEach(bar => {

            const width = bar.style.width;

            bar.style.width = "0";

            requestAnimationFrame(() => {

                setTimeout(() => {

                    bar.style.width = width;

                }, 250);

            });

        });

    }

};


/* ==========================================================
   AI REFRESH
========================================================== */

const GoalAI = {

    init() {

        const btn = document.querySelector(".goal-ai-refresh");

        if (!btn) return;

        btn.addEventListener("click", () => {

            btn.disabled = true;

            btn.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                Updating...
            `;

            setTimeout(() => {

                btn.innerHTML = `
                    <i class="fa-solid fa-check"></i>
                    Updated
                `;

                setTimeout(() => {

                    btn.disabled = false;

                    btn.innerHTML = `
                        <i class="fa-solid fa-arrows-rotate"></i>
                        Refresh Insights
                    `;

                }, 1200);

            }, 1000);

        });

    }

};


/* ==========================================================
   DELETE CONFIRMATION
========================================================== */

const GoalDelete = {

    init() {

        document.querySelectorAll(".goal-delete-btn").forEach(btn => {

            btn.addEventListener("click", e => {

                if (!confirm("Are you sure you want to delete this goal?")) {

                    e.preventDefault();

                }

            });

        });

    }

};

/* ==========================================================
   GOAL CONTRIBUTION
========================================================== */

const GoalContribution = {

    modal: null,

    form: null,

    init() {

        this.modal = document.getElementById("contribution-modal");

        this.form = document.getElementById("contribution-form");

        if (!this.modal || !this.form) return;

        this.bindButtons();

        this.bindClose();

        this.bindSubmit();

    },

    bindButtons() {

        document.querySelectorAll(".goal-contribute-btn").forEach(btn => {

            btn.addEventListener("click", () => {

                const goalId = btn.dataset.goalId;

                const title = btn.dataset.goalTitle;

                const current = parseFloat(btn.dataset.current);

                const target = parseFloat(btn.dataset.target);

                const remaining = target - current;

                document.getElementById("goal-id").value = goalId;

                document.getElementById("contribution-goal-name").innerText = title;

                document.getElementById("current-saved").innerText =
                    "₹" + current.toLocaleString();

                document.getElementById("target-amount").innerText =
                    "₹" + target.toLocaleString();

                document.getElementById("remaining-amount").innerText =
                    "₹" + remaining.toLocaleString();

                this.form.action = `/goals/${goalId}/contribute/`;

                this.modal.classList.add("show");

                document.body.style.overflow = "hidden";

            });

        });

    },

    bindClose() {

        document.getElementById("contribution-close")
            ?.addEventListener("click", () => this.close());

        document.getElementById("contribution-cancel")
            ?.addEventListener("click", () => this.close());

        this.modal.addEventListener("click", e => {

            if (e.target === this.modal) {

                this.close();

            }

        });

    },

    bindSubmit() {

        this.form.addEventListener("submit", async (e) => {

            e.preventDefault();

            const submitBtn = this.form.querySelector(".goal-save-btn");

            submitBtn.disabled = true;

            submitBtn.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                Contributing...
            `;

            try {

                const response = await fetch(this.form.action, {

                    method: "POST",

                    headers: {

                        "X-CSRFToken": this.form.querySelector("[name=csrfmiddlewaretoken]").value,

                    },

                    body: new FormData(this.form),

                });

                const data = await response.json();

                if (data.success) {

                    this.close();

                    location.reload();

                } else {

                    alert(data.message || "Contribution failed.");

                }

            } catch (error) {

                console.error(error);

                alert("Something went wrong.");

            }

            submitBtn.disabled = false;

            submitBtn.innerHTML = `
                <i class="fa-solid fa-piggy-bank"></i>
                Contribute
            `;

        });

    },

    close() {

        this.modal.classList.remove("show");

        document.body.style.overflow = "";

        this.form.reset();

    }

};