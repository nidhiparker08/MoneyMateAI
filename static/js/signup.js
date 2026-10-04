const passwords = document.querySelectorAll(".togglePassword");

passwords.forEach(icon => {
    icon.addEventListener("click", () => {
        const input = icon.previousElementSibling;
        if (input.type === "password") {
            input.type = "text";
            icon.classList.replace("fa-eye", "fa-eye-slash");
        }
        else {
            input.type = "password";
            icon.classList.replace("fa-eye-slash", "fa-eye");
        }
    });
});

const password = document.querySelectorAll("input[type=password]")[0];
const confirm = document.querySelectorAll("input[type=password]")[1];
const strength = document.getElementById("strengthText");
const match = document.getElementById("matchText");

password.addEventListener("keyup", () => {
    const value = password.value;
    let score = 0;
    if (value.length >= 8) score++;
    if (/[A-Z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^A-Za-z0-9]/.test(value)) score++;
    if (score <= 1) {
        strength.innerHTML = "Weak password"; strength.style.color = "#E5484D";
    }
    else if (score <= 3) {
        strength.innerHTML = "Medium strength"; strength.style.color = "#D98A00";
    }
    else {
        strength.innerHTML = "Strong password"; strength.style.color = "#12A150";
    }
});

confirm.addEventListener("keyup", () => {
    if (confirm.value === "") {
        match.innerHTML = "";
        return;
    }
    if (confirm.value === password.value) {
        match.innerHTML = "Passwords match";
        match.style.color = "#6ee7b7";
    }
    else {
        match.innerHTML = "Passwords don't match";
        match.style.color = "#ff8b8b";
    }
});