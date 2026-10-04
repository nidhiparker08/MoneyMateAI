(() => {

    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrf = csrfInput ? csrfInput.value : "";

    // ========= Refresh live prices =========
    const refreshBtn = document.getElementById("refresh-prices-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            const orig = refreshBtn.innerHTML;
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Fetching NSE prices…';
            try {
                const fd = new FormData();
                fd.append("csrfmiddlewaretoken", csrf);
                const res = await fetch("/investments/prices/refresh/", {
                    method: "POST",
                    body: fd,
                    headers: { "X-CSRFToken": csrf },
                    credentials: "same-origin",
                });
                const data = await res.json();
                if (data.success) {
                    if (window.showToast) {
                        window.showToast(
                            `Prices refreshed (${data.updated_count} updated${data.failed_count ? ", " + data.failed_count + " failed" : ""})`,
                            "success"
                        );
                    }
                    setTimeout(() => location.reload(), 500);
                } else {
                    if (window.showToast) window.showToast("Failed to refresh prices", "error");
                }
            } catch (e) {
                if (window.showToast) window.showToast("Network error", "error");
            } finally {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = orig;
            }
        });
    }

    // ========= Live quote in Add Holding modal =========
    const symbolInput = document.querySelector('input[name="symbol"]');
    const nameInput = document.querySelector('input[name="name"]');
    const currentPriceInput = document.querySelector('input[name="current_price"]');
    const assetTypeInput = document.querySelector('select[name="asset_type"]');
    if (symbolInput && currentPriceInput) {
        let debounce;
        const fetchQuote = async () => {
            const s = symbolInput.value.trim();
            if (s.length < 2) return;
            const at = assetTypeInput ? assetTypeInput.value : "stock";
            try {
                const res = await fetch(`/investments/quote/?symbol=${encodeURIComponent(s)}&asset_type=${at}`, {
                    credentials: "same-origin",
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.success) {
                        currentPriceInput.value = data.price;
                        currentPriceInput.classList.add("live-fetched");
                        setTimeout(() => currentPriceInput.classList.remove("live-fetched"), 1500);
                    }
                }
            } catch {}
        };
        symbolInput.addEventListener("change", () => { clearTimeout(debounce); debounce = setTimeout(fetchQuote, 200); });
        symbolInput.addEventListener("blur", fetchQuote);
    }

    // ========= Modal =========
    const modal = document.getElementById("holding-modal");
    const openBtn = document.getElementById("add-holding-btn");
    if (openBtn) openBtn.addEventListener("click", () => modal.classList.add("show"));
    document.querySelectorAll(".inv-modal-close").forEach(b =>
        b.addEventListener("click", () => modal.classList.remove("show"))
    );
    if (modal) modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.remove("show");
    });

    // ========= Add holding =========
    const holdingForm = document.getElementById("holding-form");
    if (holdingForm) {
        holdingForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fd = new FormData(holdingForm);
            const res = await fetch("/investments/holdings/add/", {
                method: "POST",
                body: fd,
                headers: { "X-CSRFToken": csrf },
                credentials: "same-origin",
            });
            const data = await res.json();
            if (data.success) {
                if (window.showToast) window.showToast("Holding added", "success");
                setTimeout(() => location.reload(), 400);
            } else {
                if (window.showToast) window.showToast("Please check the form", "error");
            }
        });
    }

    // ========= Delete holding =========
    document.querySelectorAll(".row-delete").forEach(btn => {
        btn.addEventListener("click", async () => {
            if (!confirm("Delete this holding?")) return;
            const id = btn.dataset.holdingId;
            const fd = new FormData();
            const res = await fetch(`/investments/holdings/${id}/delete/`, {
                method: "POST",
                body: fd,
                headers: { "X-CSRFToken": csrf },
                credentials: "same-origin",
            });
            const data = await res.json();
            if (data.success) {
                if (window.showToast) window.showToast("Holding removed", "success");
                setTimeout(() => location.reload(), 400);
            }
        });
    });

    // ========= AI Suggestions =========
    const suggestForm = document.getElementById("ai-suggest-form");
    const grid = document.getElementById("suggestions-grid");
    if (suggestForm) {
        suggestForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = suggestForm.querySelector('button[type="submit"]');
            btn.disabled = true;
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Thinking…';
            grid.innerHTML = '<div class="inv-empty"><i class="fa-solid fa-spinner fa-spin"></i><p>Analysing markets & building your plan…</p></div>';

            const fd = new FormData(suggestForm);
            try {
                const res = await fetch("/investments/suggestions/generate/", {
                    method: "POST",
                    body: fd,
                    headers: { "X-CSRFToken": csrf },
                    credentials: "same-origin",
                });
                const data = await res.json();
                if (data.success && data.suggestions.length) {
                    grid.innerHTML = data.suggestions.map(s => `
                        <article class="suggest-card">
                            <div class="suggest-top">
                                <div>
                                    <strong>${s.symbol}</strong>
                                    <span class="tag">${s.sector || ''}</span>
                                </div>
                                <span class="action-badge action-${(s.action || 'buy').toLowerCase()}">${(s.action || 'Buy').replace(/^./, c => c.toUpperCase())}</span>
                            </div>
                            <h4>${s.name}</h4>
                            <p class="suggest-rationale">${s.rationale || ''}</p>
                            <div class="suggest-meta">
                                <span><i class="fa-solid fa-shield"></i> ${(s.risk_level || 'medium').replace(/^./, c => c.toUpperCase())} risk</span>
                                <span><i class="fa-solid fa-clock"></i> ${s.time_horizon || ''}</span>
                                <span><i class="fa-solid fa-percent"></i> ${s.target_allocation_pct || 0}%</span>
                            </div>
                        </article>
                    `).join("");
                    if (window.showToast) window.showToast("AI suggestions ready", "success");
                } else {
                    grid.innerHTML = '<div class="inv-empty"><i class="fa-solid fa-triangle-exclamation"></i><p>Could not generate suggestions right now.</p></div>';
                }
            } catch (err) {
                grid.innerHTML = '<div class="inv-empty"><i class="fa-solid fa-triangle-exclamation"></i><p>Network error while contacting AI.</p></div>';
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }
})();
