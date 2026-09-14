const STORAGE_KEY = "kiosk-px-per-mm";
const DEFAULT_PX_PER_MM = 96 / 25.4; // CSS's built-in (usually wrong) assumption

const slider = document.getElementById("slider");
const numeric = document.getElementById("numeric");
const resetBtn = document.getElementById("reset");
const readout = document.getElementById("readout");
const frame = document.getElementById("frame");
const kioskFrame = document.getElementById("kiosk-frame");
const calibrationEl = document.getElementById("calibration");
const calSummaryEl = document.getElementById("cal-summary");

function apply(value) {
  const pxPerMm = Math.min(6, Math.max(2, Number(value) || DEFAULT_PX_PER_MM));
  document.documentElement.style.setProperty("--px-per-mm", pxPerMm);
  slider.value = pxPerMm;
  numeric.value = pxPerMm.toFixed(4);

  const framePxWidth = pxPerMm * 165;
  const scale = framePxWidth / 1024;
  kioskFrame.style.transform = `scale(${scale})`;

  const ppi = pxPerMm * 25.4;
  readout.textContent =
    `${pxPerMm.toFixed(4)} px/mm  ≈  ${ppi.toFixed(1)} PPI  ` +
    `—  165×100mm frame renders at ${framePxWidth.toFixed(0)}×${(pxPerMm * 100).toFixed(0)}px on this monitor.`;
  calSummaryEl.textContent = `(${pxPerMm.toFixed(2)} px/mm)`;

  localStorage.setItem(STORAGE_KEY, String(pxPerMm));
}

let stored = null;
try {
  stored = localStorage.getItem(STORAGE_KEY);
} catch {
  stored = null;
}
apply(stored !== null ? Number(stored) : DEFAULT_PX_PER_MM);
calibrationEl.open = stored === null;

slider.addEventListener("input", () => apply(slider.value));
numeric.addEventListener("input", () => apply(numeric.value));
resetBtn.addEventListener("click", () => apply(DEFAULT_PX_PER_MM));

document.querySelectorAll(".scene-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".scene-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    kioskFrame.src = tab.dataset.src;
  });
});
