/* ==========================================================
   Dashboard
========================================================== */

/* Navbar Button Animation */

const navButtons = document.querySelectorAll(".nav-btn");

navButtons.forEach(button => {

    button.addEventListener("click", () => {

        button.animate(
            [
                { transform: "scale(1)" },
                { transform: "scale(.92)" },
                { transform: "scale(1)" }
            ],
            {
                duration: 180
            }
        );

    });

});

/* ==========================================================
   Dashboard
========================================================== */

/* Button Animation */

document.querySelectorAll(".icon-btn").forEach(button => {

    button.addEventListener("click", () => {

        button.animate(

            [

                { transform: "scale(1)" },

                { transform: "scale(.90)" },

                { transform: "scale(1)" }

            ],

            {

                duration: 180

            }

        );

    });

});

/* ==========================================
   Dynamic Greeting
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    const greeting = document.getElementById("hero-greeting");

    if (!greeting) return;

    const hour = new Date().getHours();

    let message = "";

    if (hour >= 5 && hour < 12) {

        message = "Good Morning";

    }

    else if (hour >= 12 && hour < 17) {

        message = "Good Afternoon";

    }

    else if (hour >= 17 && hour < 21) {

        message = "Good Evening";

    }

    else {

        message = "Good Night";

    }

    const username = greeting.dataset.username;

    greeting.innerHTML = `${message}, ${username} 👋`;

});