function showToast(message, type = "info", title = "") {

    const container = document.getElementById("toastContainer");

    if (!container) return;

    const icons = {

        success: "fa-circle-check",

        error: "fa-circle-xmark",

        warning: "fa-triangle-exclamation",

        info: "fa-circle-info"

    };

    const titles = {

        success: "Success",

        error: "Error",

        warning: "Warning",

        info: "Information"

    };

    const toast = document.createElement("div");

    toast.className = `toast ${type}`;

    toast.innerHTML = `

        <div class="toast-icon">

            <i class="fa-solid ${icons[type]}"></i>

        </div>

        <div class="toast-content">

            <div class="toast-title">

                ${title || titles[type]}

            </div>

            <div class="toast-message">

                ${message}

            </div>

        </div>

        <div class="toast-close">

            <i class="fa-solid fa-xmark"></i>

        </div>

    `;

    container.appendChild(toast);

    const removeToast = () => {

        toast.classList.add("hide");

        setTimeout(() => {

            toast.remove();

        }, 350);

    };

    toast.querySelector(".toast-close").onclick = removeToast;

    setTimeout(removeToast, 3500);

}