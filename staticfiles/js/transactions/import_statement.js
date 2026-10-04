document.addEventListener("DOMContentLoaded", () => {

    const browseButton =
        document.getElementById("browseButton");

    const fileInput =
        document.getElementById("id_statement");

    if (!fileInput)
        return;

    fileInput.hidden = true;

    const uploadCard =
        document.querySelector(".upload-card");

    const uploadTitle =
        uploadCard.querySelector("h2");

    const uploadText =
        uploadCard.querySelector("p");

    const selectedFile =
        document.getElementById("selectedFile");

    const uploadButton =
        document.getElementById("uploadButton");

    // ==========================================
    // Browse Button
    // ==========================================

    browseButton.addEventListener(

        "click",

        () => {

            fileInput.click();

        }

    );

    // ==========================================
    // File Selected
    // ==========================================

    fileInput.addEventListener(

        "change",

        () => {

            if (fileInput.files.length === 0)
                return;

            validateFile(fileInput.files[0]);

        }

    );

    // ==========================================
    // Drag Events
    // ==========================================

    [

        "dragenter",

        "dragover"

    ].forEach(event => {

        uploadCard.addEventListener(

            event,

            e => {

                e.preventDefault();

                uploadCard.classList.add("dragover");

            }

        );

    });

    [

        "dragleave",

        "dragend"

    ].forEach(event => {

        uploadCard.addEventListener(

            event,

            e => {

                e.preventDefault();

                uploadCard.classList.remove("dragover");

            }

        );

    });

    uploadCard.addEventListener(

        "drop",

        e => {

            e.preventDefault();

            uploadCard.classList.remove("dragover");

            const files = e.dataTransfer.files;

            if (!files.length)
                return;

            fileInput.files = files;

            validateFile(files[0]);

        }

    );

    // ==========================================
    // Validate File
    // ==========================================

    function validateFile(file) {

        const allowed = [

            "csv",

            "xlsx",

            "xls",

            "pdf"

        ];

        const ext = file.name
            .split(".")
            .pop()
            .toLowerCase();

        if (!allowed.includes(ext)) {

            showToast(

                "Only CSV, Excel and PDF allowed.",

                "error",

                "Error"

            );

            return;

        }

        if (file.size > 25 * 1024 * 1024) {

            showToast(

                "Maximum size is 25 MB.",

                "error",

                "Error"

            );

            return;

        }

        document.getElementById("dropzoneIcon")
            .className = "fa-solid fa-circle-check";

        document.getElementById("dropzoneTitle")
            .innerHTML = "Ready to Import";

        document.getElementById("dropzoneSubtitle")
            .innerHTML = "Everything looks good.";

        document.getElementById("filePreview")
            .innerHTML =`
            <strong>${file.name}</strong><br>
            ${(file.size / 1024 / 1024).toFixed(2)} MB
        `;

        uploadButton.disabled = false;

        const progress =
            document.getElementById("progressContainer");

        const bar =
            document.getElementById("progressBar");

        progress.style.display = "block";

        let width = 0;

        const interval = setInterval(() => {

            width += 5;

            bar.style.width = width + "%";

            if (width >= 100) {

                clearInterval(interval);

            }

        }, 25);

    }

});