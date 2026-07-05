// Muse Spark Explorer Theme Switcher
document.addEventListener("DOMContentLoaded", () => {
    const themeToggleBtn = document.getElementById("theme-toggle");
    const themeIcon = themeToggleBtn ? themeToggleBtn.querySelector("i") : null;
    
    // Default to dark mode
    const getPreferredTheme = () => {
        const storedTheme = localStorage.getItem("theme");
        if (storedTheme) {
            return storedTheme;
        }
        return "dark"; // Default
    };

    const setTheme = (theme) => {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
        
        // Update button icons
        if (themeIcon) {
            if (theme == "light") {
                themeIcon.className = "bi bi-moon-stars-fill";
                themeToggleBtn.setAttribute("title", "Switch to Dark Mode");
            } else {
                themeIcon.className = "bi bi-sun-fill";
                themeToggleBtn.setAttribute("title", "Switch to Light Mode");
            }
        }
    };

    // Initialize theme on load
    const activeTheme = getPreferredTheme();
    setTheme(activeTheme);

    // Click handler for theme toggle button
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "light" ? "dark" : "light";
            setTheme(newTheme);
        });
    }

    // Handle mobile sidebar toggle
    const sidebarToggleBtn = document.getElementById("sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");
    
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            sidebar.classList.toggle("show");
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("show") && !sidebar.contains(e.target) && e.target !== sidebarToggleBtn) {
                sidebar.classList.remove("show");
            }
        });
    }
});
