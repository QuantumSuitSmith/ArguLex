// Apply the saved theme on page load
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
