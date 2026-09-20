const NOW_PLAYING_POLL_MS = 3000;
const WEATHER_POLL_MS = 10 * 60 * 1000;
const UP_NEXT_THRESHOLD_MS = 20000; // show "up next" once this close to the end

function formatTime(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function getJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// --- Clock ---

const clockEl = document.getElementById("clock");
function tickClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
tickClock();
setInterval(tickClock, 1000);

// --- Weather badge ---

const weatherEl = document.getElementById("weather");

async function pollWeather() {
  let data;
  try {
    data = await getJSON("/api/weather");
  } catch {
    weatherEl.hidden = true;
    return;
  }

  if (!data.configured || data.error) {
    weatherEl.hidden = true;
    return;
  }

  weatherEl.innerHTML = "";
  weatherEl.appendChild(el("span", "weather-icon", data.icon));
  weatherEl.appendChild(el("span", "weather-temp", `${Math.round(data.temperature)}°${data.unit}`));
  weatherEl.hidden = false;
}
pollWeather();
setInterval(pollWeather, WEATHER_POLL_MS);

// --- Now Playing ---

const bgEl = document.getElementById("bg");
const sceneEl = document.getElementById("scene-now-playing");
const idleViewEl = document.getElementById("idle-view");
const controlsBarEl = document.getElementById("controls-bar");
const artEl = document.getElementById("art");
const trackEl = document.getElementById("track");
const eqEl = document.getElementById("eq");
const artistsEl = document.getElementById("artists");
const albumCaptionEl = document.getElementById("album-caption");
const progressBar = document.getElementById("progress-bar");
const elapsedEl = document.getElementById("elapsed");
const durationEl = document.getElementById("duration");
const lyricsView = document.getElementById("lyrics-view");
const upNextCornerEl = document.getElementById("up-next-corner");
const upNextCornerArtEl = document.getElementById("up-next-corner-art");
const upNextCornerTitleEl = document.getElementById("up-next-corner-title");

let lastTrackId = null;
let currentLyrics = null;
let activeLyricsLineIndex = -1;
let releaseYear = "";
let nextTrack = null;

// Polling the API every 3s (to stay well under Spotify's rate limits) would
// make the timer/progress bar/lyrics visibly jump every 3s instead of
// ticking smoothly. Instead, resync to the authoritative progress_ms on
// each poll but interpolate locally every second in between.
let lastKnownProgressMs = 0;
let lastKnownDurationMs = 0;
let lastKnownIsPlaying = false;
let lastSyncedAt = 0;

const LYRICS_RETRY_DELAYS_MS = [2000, 5000, 10000];

async function loadLyrics(attempt = 0) {
  const forTrack = lastTrackId;
  if (attempt === 0) {
    currentLyrics = null;
    activeLyricsLineIndex = -1;
    lyricsView.innerHTML = "";
    lyricsView.appendChild(el("div", "empty", "Loading lyrics..."));
  }

  let data;
  try {
    data = await getJSON("/api/lyrics");
  } catch {
    data = { available: false, error: true };
  }

  // Track changed while this was in flight — a newer loadLyrics owns the view.
  if (forTrack !== lastTrackId) return;

  if (data.error && attempt < LYRICS_RETRY_DELAYS_MS.length) {
    setTimeout(() => loadLyrics(attempt + 1), LYRICS_RETRY_DELAYS_MS[attempt]);
    return;
  }

  if (!data.available || !data.lines || !data.lines.length) {
    lyricsView.innerHTML = "";
    lyricsView.appendChild(el("div", "empty", data.error ? "Lyrics unavailable right now." : "No lyrics available."));
    return;
  }

  currentLyrics = data;
  lyricsView.innerHTML = "";
  data.lines.forEach((line, i) => {
    const p = el("div", "lyrics-line", line.text || "♪");
    p.dataset.index = i;
    lyricsView.appendChild(p);
  });
}

function renderAlbumCaption(label) {
  const parts = [releaseYear, label].filter(Boolean);
  albumCaptionEl.textContent = parts.join(" · ");
}

async function loadAlbumExtra() {
  renderAlbumCaption(null);
  try {
    const data = await getJSON("/api/track-extra");
    renderAlbumCaption(data.label);
  } catch {
    // Leave just the release year showing.
  }
}

async function loadNextTrack() {
  nextTrack = null;
  upNextCornerEl.classList.remove("visible");
  try {
    const items = await getJSON("/api/queue");
    nextTrack = items[0] || null;
  } catch {
    nextTrack = null;
  }
  if (nextTrack) {
    upNextCornerArtEl.src = nextTrack.album_art || "";
    upNextCornerTitleEl.textContent = `${nextTrack.track} — ${nextTrack.artists}`;
    upNextCornerEl.hidden = false;
  } else {
    upNextCornerEl.hidden = true;
  }
}

function updateUpNextVisibility(progressMs, durationMs) {
  if (!nextTrack || !durationMs) return;
  const remaining = durationMs - progressMs;
  upNextCornerEl.classList.toggle("visible", remaining > 0 && remaining <= UP_NEXT_THRESHOLD_MS);
}

function updateLyricsHighlight(progressMs) {
  if (!currentLyrics || currentLyrics.sync_type !== "LINE_SYNCED" || !currentLyrics.lines.length) {
    return;
  }
  let index = -1;
  for (let i = 0; i < currentLyrics.lines.length; i++) {
    if (currentLyrics.lines[i].time_ms <= progressMs) index = i;
    else break;
  }
  if (index === activeLyricsLineIndex) return;
  activeLyricsLineIndex = index;

  const lines = lyricsView.querySelectorAll(".lyrics-line");
  lines.forEach((lineEl, i) => lineEl.classList.toggle("active", i === index));
  if (index >= 0) {
    lines[index].scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function applyProgress(progressMs, durationMs) {
  const pct = durationMs ? (progressMs / durationMs) * 100 : 0;
  progressBar.style.width = `${Math.min(100, pct)}%`;
  elapsedEl.textContent = formatTime(progressMs);
  durationEl.textContent = formatTime(durationMs);
  updateLyricsHighlight(progressMs);
  updateUpNextVisibility(progressMs, durationMs);
}

function tickProgress() {
  if (!lastKnownIsPlaying || !lastKnownDurationMs) return;
  const estimate = Math.min(lastKnownDurationMs, lastKnownProgressMs + (Date.now() - lastSyncedAt));
  applyProgress(estimate, lastKnownDurationMs);
}
setInterval(tickProgress, 150); // frequent enough that lyric-line changes feel instant, still all local (no network)

async function pollNowPlaying() {
  let data;
  try {
    data = await getJSON("/api/now-playing");
  } catch {
    return;
  }

  if (!data.track) {
    sceneEl.hidden = true;
    idleViewEl.hidden = false;
    controlsBarEl.hidden = true;
    bgEl.style.backgroundImage = "";
    lastKnownIsPlaying = false;
    if (lastTrackId !== null) {
      lastTrackId = null;
      currentLyrics = null;
      activeLyricsLineIndex = -1;
      lyricsView.innerHTML = "";
      nextTrack = null;
      upNextCornerEl.hidden = true;
      upNextCornerEl.classList.remove("visible");
    }
    return;
  }

  sceneEl.hidden = false;
  idleViewEl.hidden = true;
  controlsBarEl.hidden = false;
  eqEl.hidden = !data.is_playing;

  if (data.track !== lastTrackId) {
    lastTrackId = data.track;
    trackEl.textContent = data.track;
    artistsEl.textContent = data.artists;
    artEl.src = data.album_art || "";
    bgEl.style.backgroundImage = data.album_art ? `url(${data.album_art})` : "";
    releaseYear = data.album_release_date ? data.album_release_date.slice(0, 4) : "";
    renderAlbumCaption(null);
    loadLyrics();
    loadAlbumExtra();
    loadNextTrack();
  }

  lastKnownProgressMs = data.progress_ms;
  lastKnownDurationMs = data.duration_ms;
  lastKnownIsPlaying = data.is_playing;
  lastSyncedAt = Date.now();
  applyProgress(data.progress_ms, data.duration_ms);
}

pollNowPlaying();
setInterval(pollNowPlaying, NOW_PLAYING_POLL_MS);

// --- Playback controls (keyboard stand-in for the future rotary knob) ---

async function playerAction(endpoint) {
  try {
    await fetch(endpoint, { method: "POST" });
  } catch {
    // Ignore — next poll will just show whatever the real state is.
  }
  setTimeout(pollNowPlaying, 300);
}

document.getElementById("btn-prev").addEventListener("click", () => playerAction("/api/player/previous"));
document.getElementById("btn-toggle").addEventListener("click", () => playerAction("/api/player/toggle"));
document.getElementById("btn-next").addEventListener("click", () => playerAction("/api/player/next"));

document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") {
    playerAction("/api/player/previous");
  } else if (event.key === "ArrowRight") {
    playerAction("/api/player/next");
  } else if (event.key === " ") {
    event.preventDefault();
    playerAction("/api/player/toggle");
  }
});
