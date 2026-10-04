(() => {

    const form = document.getElementById("ai-chat-form");
    const textarea = document.getElementById("ai-chat-text");
    const scroll = document.getElementById("ai-chat-scroll");
    const clearBtn = document.querySelector('[data-testid="ai-clear-btn"]');
    const refreshBtn = document.querySelector('[data-testid="refresh-insights-btn"]');

    if (!form) return;

    const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

    function autoResize() {
        textarea.style.height = "auto";
        textarea.style.height = Math.min(textarea.scrollHeight, 180) + "px";
    }
    textarea.addEventListener("input", autoResize);
    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    // suggestion chips
    document.querySelectorAll(".ai-suggest-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            textarea.value = chip.textContent.trim();
            autoResize();
            textarea.focus();
        });
    });

    function bubble(role, text, {typing=false} = {}) {
        const wrap = document.createElement("div");
        wrap.className = `chat-bubble bubble-${role}`;
        const avatar = document.createElement("div");
        avatar.className = "bubble-avatar";
        avatar.innerHTML = role === "user"
            ? (window.__FS_USER_INITIAL || "U")
            : '<i class="fa-solid fa-robot"></i>';
        const body = document.createElement("div");
        body.className = "bubble-body";
        if (typing) {
            body.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
        } else {
            body.textContent = text;
        }
        wrap.appendChild(avatar);
        wrap.appendChild(body);
        // Remove welcome block on first message
        const welcome = scroll.querySelector(".ai-welcome");
        if (welcome) welcome.remove();
        scroll.appendChild(wrap);
        scroll.scrollTop = scroll.scrollHeight;
        return body;
    }

    async function sendMessage(text) {
        bubble("user", text);
        const bodyEl = bubble("assistant", "", {typing: true});
        const fd = new FormData();
        fd.append("message", text);
        try {
            const res = await fetch("/ai/chat/", {
                method: "POST",
                body: fd,
                headers: { "X-CSRFToken": csrf },
                credentials: "same-origin",
            });
            const data = await res.json();
            if (data.success) {
                bodyEl.textContent = data.reply;
            } else {
                bodyEl.textContent = data.message || "Something went wrong.";
                bodyEl.classList.add("error");
            }
        } catch (e) {
            bodyEl.textContent = "Network error — please try again.";
            bodyEl.classList.add("error");
        } finally {
            scroll.scrollTop = scroll.scrollHeight;
            refreshInsights();
        }
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const t = textarea.value.trim();
        if (!t) return;
        textarea.value = "";
        autoResize();
        sendMessage(t);
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", async () => {
            if (!confirm("Clear chat history?")) return;
            const fd = new FormData();
            fd.append("csrfmiddlewaretoken", csrf);
            await fetch("/ai/clear/", {
                method: "POST",
                body: fd,
                headers: { "X-CSRFToken": csrf },
                credentials: "same-origin",
            });
            scroll.innerHTML = "";
            location.reload();
        });
    }

    async function refreshInsights() {
        try {
            const res = await fetch("/ai/insights/", { credentials: "same-origin" });
            const data = await res.json();
            const list = document.getElementById("ai-insights-list");
            if (!list || !data.insights) return;
            list.innerHTML = data.insights.map(i => `
                <li class="insight-item tone-${i.tone}">
                    <i class="fa-solid ${i.icon}"></i>
                    <div>
                        <strong>${i.title}</strong>
                        <span>${i.body}</span>
                    </div>
                </li>
            `).join("");
        } catch {}
    }

    if (refreshBtn) refreshBtn.addEventListener("click", refreshInsights);

})();
