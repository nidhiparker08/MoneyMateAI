document.addEventListener("DOMContentLoaded", () => {

    // Loading Screen
    window.onload = () => {
        setTimeout(() => {
            document.getElementById("loader").style.opacity = "0";
            setTimeout(() => {
                document.getElementById("loader").style.display = "none";
            }, 500);
        }, 800);
    };

    // Reveal Animation
    const reveals = document.querySelectorAll(".reveal");
    function revealSections() {
        reveals.forEach(section => {
            const top = section.getBoundingClientRect().top;
            if (top < window.innerHeight - 120) {
                section.classList.add("active");
            }
        });
    }
    revealSections();
    window.addEventListener("scroll", revealSections);

    // Counter Animation
    const counters = document.querySelectorAll(".counter");
    let counterStarted = false;
    function startCounters() {
        const aboutSection = document.querySelector(".about");
        if (!aboutSection || counterStarted) return;
        const top = aboutSection.getBoundingClientRect().top;
        if (top < window.innerHeight - 150) {
            counterStarted = true;
            counters.forEach(counter => {
                const target = parseFloat(counter.dataset.target);
                let current = 0;
                const increment = target / 150;
                function update() {
                    if (current < target) {
                        current += increment;
                        if (target % 1 !== 0) {
                            counter.textContent = current.toFixed(1);
                        } else {
                            counter.textContent = Math.ceil(current);
                        }
                        requestAnimationFrame(update);
                    } else {
                        if (target % 1 !== 0) {
                            counter.textContent = target.toFixed(1);
                        } else {
                            counter.textContent = target;
                        }
                    }
                }
                update();
            });
        }
    }
    startCounters();
    window.addEventListener("scroll", startCounters);

    // Mouse Glow
    const glow = document.querySelector(".cursor-glow");
    let mouseX = 0;
    let mouseY = 0;
    let currentX = 0;
    let currentY = 0;
    document.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    function animateGlow() {
        currentX += (mouseX - currentX) * 0.12;
        currentY += (mouseY - currentY) * 0.12;
        glow.style.left = currentX + "px";
        glow.style.top = currentY + "px";
        requestAnimationFrame(animateGlow);
    }
    animateGlow();
});