const progressFill = document.getElementById("progress-fill");
const progressPercent = document.getElementById("progress-percent");

// Read the house from the URL
const params = new URLSearchParams(window.location.search);
const house = params.get("housedata/houses.json");

// Load the JSON
fetch("houses.json")
  .then(response => response.json())
  .then(houses => {

    // Find the house
    const houseData = houses[house];

    if (!houseData) {
      progressPercent.textContent = "0%";
      progressFill.style.width = "0%";
      console.log("House not found");
      return;
    }

    animateProgress(houseData.progress);

    // Optional: show the resident's name
    const name = document.getElementById("resident-name");
    if (name) {
      name.textContent = houseData.residentName;
    }

    // Optional: show a message
    const message = document.getElementById("message");
    if (message) {
      message.textContent = houseData.message;
    }

  });

function animateProgress(target) {

  let current = 0;

  function step() {

    if (current >= target) return;

    current++;

    progressFill.style.width = current + "%";
    progressPercent.textContent = current + "%";

    requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}
