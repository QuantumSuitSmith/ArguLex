document.addEventListener("DOMContentLoaded", function () {

    // Theme Toggle Functionality
    document.getElementById("modeToggle").addEventListener("change", function () {
      const theme = document.documentElement.getAttribute("data-theme");
      document.documentElement.setAttribute("data-theme", theme === "dark" ? "light" : "dark");
    });
  
    // Redirect to Create Account page when "Try Argulex" button is clicked
    const tryButton = document.getElementById("tryBtn");
  
    if (tryButton) {
      tryButton.addEventListener("click", function () {
        window.location.href = "createaccount.html"; // Ensure this path is correct
      });
    } else {
      console.log("Button not found!");
    }
  });
  

  
