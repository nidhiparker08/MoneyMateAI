/* Review Queue interactions.
 *
 * Handles inline "learn & apply" forms and dismiss buttons.
 */
(function () {
    "use strict";

    function getCsrfToken() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : "";
    }

    function showToast(msg, type) {
        if (window.showToast) return window.showToast(msg, type);
        console.log("[toast]", type, msg);
    }

    async function postForm(url, formData) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken() },
            body: formData,
            credentials: "same-origin",
        });
        return res.json();
    }

    // Submit "learn & apply" form.
    document.querySelectorAll(".review-form").forEach(form => {
        form.addEventListener("submit", async (evt) => {
            evt.preventDefault();
            const id = form.dataset.itemId;
            const fd = new FormData(form);
            const submitBtn = form.querySelector("button[type=submit]");
            const originalHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Learning…';
            try {
                const data = await postForm(`/memory/review/${id}/resolve/`, fd);
                if (data.success) {
                    showToast(data.message || "Memory updated.", "success");
                    const card = document.getElementById(`item-${id}`);
                    if (card) card.style.transition = "opacity .3s";
                    if (card) card.style.opacity = 0;
                    setTimeout(() => card && card.remove(), 350);
                } else {
                    showToast(data.message || "Failed to resolve.", "error");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHtml;
                }
            } catch (e) {
                showToast("Network error while resolving.", "error");
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
            }
        });
    });

    // Dismiss buttons
    document.querySelectorAll("[data-dismiss]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.dismiss;
            if (!confirm("Dismiss this item? It will remain in your transaction list but won't ask for classification.")) return;
            const data = await postForm(`/memory/review/${id}/dismiss/`, new FormData());
            if (data.success) {
                const card = document.getElementById(`item-${id}`);
                card && card.remove();
                showToast("Dismissed.", "success");
            }
        });
    });
})();
