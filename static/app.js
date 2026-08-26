const NOW_PLAYING_POLL_MS = 3000;

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

function renderList(container, items, { image, title, subtitle }) {
  container.innerHTML = "";
  if (!items.length) {
    container.appendChild(el("div", "empty", "Nothing here yet."));
    return;
  }
  for (const item of items) {
    const row = el("div", "row");
    const img = document.createElement("img");
    img.className = "row-art";
    img.src = image(item) || "";
    img.alt = "";
    const text = el("div", "row-text");
    text.appendChild(el("div", "row-title", title(item)));
    const sub = subtitle(item);
    if (sub) text.appendChild(el("div", "row-subtitle", sub));
    row.appendChild(img);
    row.appendChild(text);
    container.appendChild(row);
  }
}

function renderGrid(container, items, { image, title, subtitle }) {
  container.innerHTML = "";
  if (!items.length) {
    container.appendChild(el("div", "empty", "Nothing here yet."));
    return;
  }
  for (const item of items) {
    const card = el("div", "card");
    const img = document.createElement("img");
    img.className = "card-art";
    img.src = image(item) || "";
    img.alt = "";
    card.appendChild(img);
    card.appendChild(el("div", "card-title", title(item)));
    const sub = subtitle(item);
    if (sub) card.appendChild(el("div", "card-subtitle", sub));
    container.appendChild(card);
  }
}

async function getJSON(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// --- Now Playing + controls ---

const art = document.getElementById("art");
const trackEl = document.getElementById("track");
const artistsEl = document.getElementById("artists");
const progressBar = document.getElementById("progress-bar");
const elapsedEl = document.getElementById("elapsed");
const durationEl = document.getElementById("duration");
const deviceInfoEl = document.getElementById("device-info");
const volumeSlider = document.getElementById("volume");
const playerErrorEl = document.getElementById("player-error");

let lastTrackId = null;
let userIsDraggingVolume = false;

async function pollNowPlaying() {
  let data;
  try {
    data = await getJSON("/api/now-playing");
  } catch {
    return;
  }

  if (!data.track) {
    trackEl.textContent = "Nothing is currently playing";
    artistsEl.textContent = "";
    art.src = "";
    progressBar.style.width = "0%";
    elapsedEl.textContent = "0:00";
    durationEl.textContent = "0:00";
    deviceInfoEl.textContent = "";
    lastTrackId = null;
    return;
  }

  if (data.track !== lastTrackId) {
    lastTrackId = data.track;
    trackEl.textContent = data.track;
    artistsEl.textContent = data.artists;
    art.src = data.album_art || "";
  }

  const pct = data.duration_ms ? (data.progress_ms / data.duration_ms) * 100 : 0;
  progressBar.style.width = `${Math.min(100, pct)}%`;
  elapsedEl.textContent = formatTime(data.progress_ms);
  durationEl.textContent = formatTime(data.duration_ms);
  deviceInfoEl.textContent = data.device_name
    ? `${data.device_name} · ${data.shuffle_state ? "shuffle on" : "shuffle off"} · repeat: ${data.repeat_state}`
    : "";

  if (!userIsDraggingVolume && typeof data.volume_percent === "number") {
    volumeSlider.value = data.volume_percent;
  }
}

async function playerAction(url, body) {
  playerErrorEl.textContent = "";
  try {
    await getJSON(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    setTimeout(pollNowPlaying, 300);
  } catch (err) {
    playerErrorEl.textContent = err.message;
  }
}

document.getElementById("btn-toggle").addEventListener("click", () => playerAction("/api/player/toggle"));
document.getElementById("btn-next").addEventListener("click", () => playerAction("/api/player/next"));
document.getElementById("btn-prev").addEventListener("click", () => playerAction("/api/player/previous"));

let shuffleOn = false;
document.getElementById("btn-shuffle").addEventListener("click", () => {
  shuffleOn = !shuffleOn;
  playerAction("/api/player/shuffle", { state: shuffleOn });
});

volumeSlider.addEventListener("input", () => {
  userIsDraggingVolume = true;
});
volumeSlider.addEventListener("change", () => {
  playerAction("/api/player/volume", { volume: Number(volumeSlider.value) });
  userIsDraggingVolume = false;
});

pollNowPlaying();
setInterval(pollNowPlaying, NOW_PLAYING_POLL_MS);

// --- Tabs ---

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
const loadedTabs = new Set();

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    const name = tab.dataset.tab;
    document.getElementById(`panel-${name}`).classList.add("active");
    if (!loadedTabs.has(name)) {
      loadedTabs.add(name);
      loaders[name] && loaders[name]();
    }
  });
});

// --- Panel loaders ---

async function loadRecent() {
  const container = document.getElementById("recent-list");
  try {
    const items = await getJSON("/api/recently-played");
    renderList(container, items, {
      image: (i) => i.album_art,
      title: (i) => i.track,
      subtitle: (i) => i.artists,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

async function loadTopTracks(timeRange = "short_term") {
  const container = document.getElementById("top-tracks-list");
  try {
    const items = await getJSON(`/api/top-tracks?time_range=${timeRange}`);
    renderList(container, items, {
      image: (i) => i.album_art,
      title: (i) => i.track,
      subtitle: (i) => i.artists,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

async function loadTopArtists(timeRange = "short_term") {
  const container = document.getElementById("top-artists-list");
  try {
    const items = await getJSON(`/api/top-artists?time_range=${timeRange}`);
    renderGrid(container, items, {
      image: (i) => i.image,
      title: (i) => i.name,
      subtitle: (i) => i.genres,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

async function loadPlaylists() {
  const container = document.getElementById("playlists-list");
  try {
    const items = await getJSON("/api/playlists");
    renderGrid(container, items, {
      image: (i) => i.image,
      title: (i) => i.name,
      subtitle: (i) => `${i.track_count} tracks · ${i.owner}`,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

async function loadSaved() {
  const container = document.getElementById("saved-list");
  try {
    const items = await getJSON("/api/saved-tracks");
    renderList(container, items, {
      image: (i) => i.album_art,
      title: (i) => i.track,
      subtitle: (i) => i.artists,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

async function loadFollowing() {
  const container = document.getElementById("following-list");
  try {
    const items = await getJSON("/api/followed-artists");
    renderGrid(container, items, {
      image: (i) => i.image,
      title: (i) => i.name,
      subtitle: (i) => `${i.followers.toLocaleString()} followers`,
    });
  } catch (err) {
    container.innerHTML = "";
    container.appendChild(el("div", "empty", err.message));
  }
}

const loaders = {
  recent: loadRecent,
  "top-tracks": () => loadTopTracks("short_term"),
  "top-artists": () => loadTopArtists("short_term"),
  playlists: loadPlaylists,
  saved: loadSaved,
  following: loadFollowing,
  search: () => {},
};

document.querySelectorAll(".range-select").forEach((group) => {
  group.querySelectorAll(".range").forEach((btn) => {
    btn.addEventListener("click", () => {
      group.querySelectorAll(".range").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const target = group.dataset.target;
      const range = btn.dataset.range;
      if (target === "top-tracks") loadTopTracks(range);
      if (target === "top-artists") loadTopArtists(range);
    });
  });
});

// Load the first tab's data immediately.
loadedTabs.add("recent");
loadRecent();

// --- Search ---

const searchInput = document.getElementById("search-input");
const searchType = document.getElementById("search-type");
const searchList = document.getElementById("search-list");
let searchDebounce = null;

async function runSearch() {
  const q = searchInput.value.trim();
  if (!q) {
    searchList.innerHTML = "";
    return;
  }
  try {
    const items = await getJSON(`/api/search?q=${encodeURIComponent(q)}&type=${searchType.value}`);
    renderGrid(searchList, items, {
      image: (i) => i.image,
      title: (i) => i.name,
      subtitle: (i) => i.subtitle,
    });
  } catch (err) {
    searchList.innerHTML = "";
    searchList.appendChild(el("div", "empty", err.message));
  }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(runSearch, 400);
});
searchType.addEventListener("change", runSearch);
