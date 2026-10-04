document.addEventListener("DOMContentLoaded", function() {

    const modal = document.getElementById("customReportModal");

    const openBtn = document.getElementById("customReportBtn");

    const closeBtn = document.getElementById("closeCustomModal");

    if (!modal) return;

    function openModal() {

        modal.classList.add("show");

    }

    function closeModal() {

        modal.classList.remove("show");

    }

    if (openBtn) {

        openBtn.addEventListener("click", openModal);

    }

    if (closeBtn) {

        closeBtn.addEventListener("click", closeModal);

    }

    modal.addEventListener("click", function(e) {

        if (e.target === modal) {

            closeModal();

        }

    });

    // Custom report download handling
    const confirmBtn = document.getElementById("confirmCustomDownload");
    const startInput = document.getElementById("customStartDate");
    const endInput = document.getElementById("customEndDate");

    if (confirmBtn) {

        confirmBtn.addEventListener("click", function() {

            const start = startInput && startInput.value;

            const end = endInput && endInput.value;

            if (!start || !end) {

                showToast("Please select both start and end dates.", "warning", "Warning");

                return;

            }

            const base = modal.dataset.downloadUrl || "/reports/download/";

            const url = `${base}?period=custom&start=${start}&end=${end}`;

            window.location.href = url;

        });

    }

});