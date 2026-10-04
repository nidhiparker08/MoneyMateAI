document.addEventListener("DOMContentLoaded", () => {

    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("sidebar-toggle");
    const overlay = document.getElementById("sidebar-overlay");
    const layout = document.querySelector(".dashboard-layout");

    if (!sidebar || !toggle) return;

    toggle.addEventListener("click", () => {

        if (window.innerWidth <= 992) {

            sidebar.classList.toggle("show");

            if (overlay) {
                overlay.classList.toggle("show");
            }

        } else {

            layout.classList.toggle("collapsed");

        }

    });

    if (overlay) {

        overlay.addEventListener("click", () => {

            sidebar.classList.remove("show");

            overlay.classList.remove("show");

        });

    }

    document.querySelectorAll(".sidebar .menu-item").forEach(item => {

        item.addEventListener("click", () => {

            if (window.matchMedia("(max-width: 992px)").matches) {

                sidebar.classList.remove("show");

                overlay.classList.remove("show");

            }

        });

    });

});