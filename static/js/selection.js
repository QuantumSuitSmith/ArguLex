// Load saved theme
const storedTheme = localStorage.getItem("theme") || "light";
document.documentElement.setAttribute("data-theme", storedTheme);

document.addEventListener("DOMContentLoaded", function () {
    const modeToggle = document.getElementById("modeToggle");

    if (modeToggle) {
        modeToggle.checked = storedTheme === "dark";

        modeToggle.addEventListener("change", function () {
            const newTheme = modeToggle.checked ? "dark" : "light";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
        });
    }
});

// Function to handle chatbot selection
function selectChatbot(type) {
    const button = event.target;
    const originalText = button.textContent;
    
    // Disable button and show loading state
    button.disabled = true;
    button.textContent = 'Loading...';
    
    // Redirect to the appropriate chat page
    window.location.href = `/chat/${type}`;
}

// Add hover effects to cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.chatbot-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
        });
    });
}); 