const progressFill = document.getElementById('progress-fill');
const progressPercent = document.getElementById('progress-percent');

const TARGET = 42;

function animateProgress() {
  let current = 0;
  const step = () => {
    if (current >= TARGET) return;
    current = Math.min(current + 1, TARGET);
    progressFill.style.width = `${current}%`;
    progressPercent.textContent = `${current}%`;
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

window.addEventListener('load', () => {
  setTimeout(animateProgress, 600);
});
