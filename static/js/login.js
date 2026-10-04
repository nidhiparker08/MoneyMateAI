// Toggle password button

const password = document.getElementById("password");
const toggle = document.getElementById("togglePassword");

toggle.addEventListener("click", () => {
    if (password.type === "password") {
        password.type = "text";
        toggle.classList.remove("fa-eye");
        toggle.classList.add("fa-eye-slash");
    }
    else {
        password.type = "password";
        toggle.classList.remove("fa-eye-slash");
        toggle.classList.add("fa-eye");
    }
});

// Loading button animation

const form = document.querySelector("form");
const button = document.getElementById("loginButton");

form.addEventListener("submit", () => {
    button.innerHTML =`
    <i class="fa-solid fa-spinner fa-spin"></i>
    Logging In...
    `;
    button.disabled = true;

});