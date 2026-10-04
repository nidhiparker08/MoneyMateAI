/* Global toast helper. Reused by every AJAX flow. */
(function () {
    window.FinToast = function (message, type = "info", duration = 3200) {
        let container = document.getElementById("toastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "toastContainer";
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        const el = document.createElement("div");
        el.className = `toast toast-${type}`;
        el.innerHTML = `
            <i class="fa-solid ${
                type === "success" ? "fa-circle-check" :
                type === "error"   ? "fa-triangle-exclamation" :
                type === "warning" ? "fa-triangle-exclamation" :
                                     "fa-circle-info"
            }"></i>
            <span>${String(message).replace(/</g, "&lt;")}</span>
        `;
        container.appendChild(el);
        requestAnimationFrame(() => el.classList.add("show"));
        setTimeout(() => {
            el.classList.remove("show");
            setTimeout(() => el.remove(), 400);
        }, duration);
    };
})();
