const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const statusEl = document.getElementById("status");
const grid = document.getElementById("grid");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(text, isError) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", Boolean(isError));
}

async function loadGallery() {
  let items;
  try {
    items = await fetch("/api/wallpapers/list").then((r) => r.json());
  } catch {
    grid.innerHTML = "";
    grid.appendChild(el("div", "empty-note", "Couldn't load photos."));
    return;
  }

  grid.innerHTML = "";
  if (!items.length) {
    grid.appendChild(el("div", "empty-note", "No photos yet — add some above."));
    return;
  }

  for (const item of items) {
    const card = el("div", "card");
    const img = document.createElement("img");
    img.src = item.url;
    img.alt = "";
    const del = el("button", "delete", "×");
    del.title = "Delete";
    del.addEventListener("click", async () => {
      del.disabled = true;
      try {
        await fetch(`/api/wallpapers/${encodeURIComponent(item.filename)}`, { method: "DELETE" });
        loadGallery();
      } catch {
        setStatus("Couldn't delete that photo.", true);
        del.disabled = false;
      }
    });
    card.appendChild(img);
    card.appendChild(del);
    grid.appendChild(card);
  }
}

async function uploadFiles(fileList) {
  const files = Array.from(fileList).filter((f) => f.type.startsWith("image/"));
  if (!files.length) return;

  const formData = new FormData();
  files.forEach((f) => formData.append("photos", f));

  setStatus(`Uploading ${files.length} photo${files.length > 1 ? "s" : ""}...`);

  let result;
  try {
    const res = await fetch("/api/wallpapers/upload", { method: "POST", body: formData });
    result = await res.json();
  } catch {
    setStatus("Upload failed — check your connection.", true);
    return;
  }

  const uploadedCount = result.uploaded.length;
  const rejectedCount = result.rejected.length;

  if (rejectedCount && uploadedCount) {
    setStatus(`Added ${uploadedCount}, skipped ${rejectedCount} (not a supported photo).`, true);
  } else if (rejectedCount) {
    setStatus(`Couldn't add ${rejectedCount} file${rejectedCount > 1 ? "s" : ""} — not a supported photo.`, true);
  } else {
    setStatus(`Added ${uploadedCount} photo${uploadedCount > 1 ? "s" : ""}.`);
  }

  loadGallery();
}

fileInput.addEventListener("change", () => {
  uploadFiles(fileInput.files);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
  });
});

dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer && e.dataTransfer.files.length) {
    uploadFiles(e.dataTransfer.files);
  }
});

loadGallery();
