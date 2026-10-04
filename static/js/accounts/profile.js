/* Profile page JS — handles avatar preview + AJAX save */
(function () {
    const form = document.getElementById("profile-form");
    if (!form) return;

    const avatarInput = document.getElementById("avatar-input");
    const preview = document.getElementById("profile-avatar-preview");
    const fallback = document.querySelector(".profile-avatar-fallback");

    // Live avatar preview.
    if (avatarInput) {
        avatarInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const url = URL.createObjectURL(file);
            if (preview) {
                preview.src = url;
            } else if (fallback) {
                const img = document.createElement("img");
                img.className = "profile-avatar-img";
                img.id = "profile-avatar-preview";
                img.src = url;
                img.alt = "Avatar";
                fallback.replaceWith(img);
            }
        });
    }

    // AJAX submit
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = new FormData(form);
        const btn = form.querySelector('button[type="submit"]');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

        try {
            const res = await fetch(form.action, {
                method: "POST",
                body: data,
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            const j = await res.json();
            if (j.success) {
                if (window.FinToast) window.FinToast("Profile updated", "success");
                else alert("Profile updated");
            } else {
                if (window.FinToast) window.FinToast(j.message || "Update failed", "error");
                else alert(j.message || "Update failed");
            }
        } catch (err) {
            if (window.FinToast) window.FinToast("Network error", "error");
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    });
})();
