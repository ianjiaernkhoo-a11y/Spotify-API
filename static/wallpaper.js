const ROTATE_MS = 20000; // how long each wallpaper stays up

const layerA = document.getElementById("layer-a");
const layerB = document.getElementById("layer-b");
const clockEl = document.getElementById("clock");
const emptyEl = document.getElementById("empty");

function tickClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
tickClock();
setInterval(tickClock, 1000);

let images = [];
let index = 0;
let showingA = true;

function preload(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

async function showNext() {
  if (!images.length) return;

  const url = images[index % images.length];
  index += 1;

  const ok = await preload(url);
  if (!ok) {
    // Skip broken files without breaking the rotation.
    if (images.length > 1) showNext();
    return;
  }

  const incoming = showingA ? layerB : layerA;
  const outgoing = showingA ? layerA : layerB;
  incoming.querySelector(".layer-bg").style.backgroundImage = `url("${url}")`;
  incoming.querySelector(".layer-fg").src = url;
  incoming.classList.add("visible");
  outgoing.classList.remove("visible");
  showingA = !showingA;
}

async function init() {
  try {
    const res = await fetch("/api/wallpapers");
    images = await res.json();
  } catch {
    images = [];
  }

  if (!images.length) {
    emptyEl.hidden = false;
    return;
  }

  emptyEl.hidden = true;
  showNext();
  setInterval(showNext, ROTATE_MS);
}

init();
