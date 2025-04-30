document.addEventListener("DOMContentLoaded", function () {

  const tryButton = document.getElementById("tryBtn");

  if (tryButton) {
    tryButton.addEventListener("click", function () {
      window.location.href = "createaccount.html"; 
    });
  } else {
    console.log("Button not found!");
  }
});



  
