"use strict";

const element = (id) => document.getElementById(id);
const pilotInput = element("pilot-file");
const workspace = element("annotation-workspace");
const notes = element("notes");
const previous = element("previous");
const next = element("next");
const nextPending = element("next-pending");
const exportButton = element("export");
const numberFormat = new Intl.NumberFormat("es-MX");
const pairKey = ({ query_id, candidate_id }) => JSON.stringify([query_id, candidate_id]);
const validScore = (score) => typeof score === "number" && score >= 0 && score <= 5 && Number.isInteger(score * 2);
const complete = (rating) => validScore(rating?.theme) && validScore(rating?.emotion);
let pilot;
let ratings = new Map();
let position = 0;
let loadAttempt = 0;

function setStatus(id, message, isError = false) {
  const status = element(id);
  status.textContent = message;
  status.classList.toggle("annotation-error", isError);
}

function makeScale(name) {
  const field = element(name + "-rating");
  const control = document.createElement("div");
  control.className = "annotation-rating-control";
  const stars = document.createElement("div");
  stars.className = "annotation-stars";
  const inputs = [];
  const fills = [];
  const result = document.createElement("div");
  result.className = "annotation-rating-result";
  const output = document.createElement("output");
  output.setAttribute("aria-label", field.querySelector("legend").textContent);
  const clear = document.createElement("button");
  clear.type = "button";
  clear.textContent = "Quitar valoración";
  clear.setAttribute("aria-label", "Quitar valoración de " + field.querySelector("legend").textContent.toLowerCase());

  function option(value, visibleText) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = name;
    input.value = value;
    input.setAttribute("aria-label", numberFormat.format(value) + (value === 1 ? " estrella" : " estrellas"));
    input.setAttribute("aria-describedby", name + "-help");
    input.addEventListener("change", () => updateRating(name, value));
    inputs.push(input);
    label.append(input, visibleText);
    return label;
  }

  const zero = option(0, "0");
  zero.className = "annotation-zero";
  control.append(zero, stars);
  for (let index = 0; index < 5; index += 1) {
    const star = document.createElement("div");
    star.className = "annotation-star";
    const outline = document.createElement("span");
    const fill = document.createElement("span");
    outline.textContent = "☆";
    fill.textContent = "★";
    fill.className = "star-fill";
    outline.setAttribute("aria-hidden", "true");
    fill.setAttribute("aria-hidden", "true");
    fills.push(fill);
    star.append(outline, fill, option(index + 0.5, ""), option(index + 1, ""));
    stars.append(star);
  }
  clear.addEventListener("click", () => {
    updateRating(name, null);
    inputs[0].focus();
  });
  result.append(output, clear);
  field.append(control, result);

  return (value) => {
    inputs.forEach((input) => { input.checked = value === Number(input.value); });
    fills.forEach((fill, index) => {
      const percent = Math.max(0, Math.min(1, (value ?? 0) - index)) * 100;
      fill.style.setProperty("--star-fill", percent + "%");
    });
    output.textContent = value === null ? "Sin valorar" : numberFormat.format(value) + " / 5";
    clear.disabled = value === null;
  };
}

const showTheme = makeScale("theme");
const showEmotion = makeScale("emotion");

function validatePilot(data) {
  if (!data || typeof data.pilot_id !== "string" || !data.pilot_id.trim()
      || !data.tracks || typeof data.tracks !== "object" || Array.isArray(data.tracks)
      || !Array.isArray(data.pairs) || !data.pairs.length) {
    throw new Error("El archivo debe contener las letras y comparaciones del piloto.");
  }
  const trackIds = Object.keys(data.tracks);
  if (trackIds.length > 200) {
    throw new Error("El archivo supera el límite de 200 letras.");
  }
  for (const track of Object.values(data.tracks)) {
    if (!track || typeof track.title !== "string" || typeof track.artist !== "string"
        || typeof track.text !== "string" || !track.text.trim()) {
      throw new Error("Hay una letra con datos incompletos en el archivo.");
    }
  }
  const seen = new Set();
  for (const pair of data.pairs) {
    if (!pair || typeof pair.query_id !== "string" || typeof pair.candidate_id !== "string"
        || pair.query_id === pair.candidate_id || !Object.hasOwn(data.tracks, pair.query_id)
        || !Object.hasOwn(data.tracks, pair.candidate_id) || seen.has(pairKey(pair))) {
      throw new Error("Hay una comparación inválida o repetida en el archivo.");
    }
    seen.add(pairKey(pair));
  }
  return data;
}

function storageKey() {
  return "sonora:anotacion:" + pilot.pilot_id;
}

function restoreProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()));
    const savedRatings = new Map(saved?.ratings ?? []);
    for (const pair of pilot.pairs) {
      const key = pairKey(pair);
      const rating = savedRatings.get(key);
      if (!rating) continue;
      ratings.set(key, {
        theme: validScore(rating.theme) ? rating.theme : null,
        emotion: validScore(rating.emotion) ? rating.emotion : null,
        notes: typeof rating.notes === "string" ? rating.notes.slice(0, 2000) : "",
      });
    }
    if (Number.isInteger(saved?.position) && saved.position >= 0 && saved.position < pilot.pairs.length) {
      position = saved.position;
    }
    return true;
  } catch {
    return false;
  }
}

function saveProgress() {
  try {
    localStorage.setItem(storageKey(), JSON.stringify({ position, ratings: [...ratings] }));
    setStatus("save-status", "Progreso guardado en este navegador.");
  } catch {
    setStatus("save-status", "El navegador no pudo guardar el progreso. Exporta tus valoraciones antes de cerrar.", true);
  }
}

function updateRating(field, value) {
  const key = pairKey(pilot.pairs[position]);
  const rating = ratings.get(key) ?? { theme: null, emotion: null, notes: "" };
  rating[field] = value;
  ratings.set(key, rating);
  saveProgress();
  renderControls();
}

function pendingPosition() {
  const count = pilot.pairs.length;
  for (let offset = 1; offset < count; offset += 1) {
    const index = (position + offset) % count;
    if (!complete(ratings.get(pairKey(pilot.pairs[index])))) return index;
  }
  return -1;
}

function renderControls() {
  const rating = ratings.get(pairKey(pilot.pairs[position]));
  showTheme(rating?.theme ?? null);
  showEmotion(rating?.emotion ?? null);
  const count = pilot.pairs.filter((pair) => complete(ratings.get(pairKey(pair)))).length;
  const progress = element("progress");
  progress.max = pilot.pairs.length;
  progress.value = count;
  element("progress-count").textContent = count + " de " + progress.max + " comparaciones completas";
  previous.disabled = position === 0;
  next.disabled = position + 1 === pilot.pairs.length;
  nextPending.disabled = pendingPosition() === -1;
  exportButton.disabled = count === 0;
}

function showPair() {
  const pair = pilot.pairs[position];
  for (const [side, id] of [["query", pair.query_id], ["candidate", pair.candidate_id]]) {
    const track = pilot.tracks[id];
    element(side + "-title").textContent = track.title;
    element(side + "-artist").textContent = track.artist;
    const lyrics = element(side + "-text");
    lyrics.textContent = track.text;
    lyrics.scrollTop = 0;
  }
  element("pair-heading").textContent = "Comparación " + (position + 1) + " de " + pilot.pairs.length;
  notes.value = ratings.get(pairKey(pair))?.notes ?? "";
  renderControls();
}

function navigate(index) {
  if (index < 0 || index >= pilot.pairs.length) return;
  position = index;
  saveProgress();
  showPair();
  element("pair-heading").focus({ preventScroll: true });
  document.querySelector(".annotation-lyrics").scrollIntoView({ block: "start" });
}

pilotInput.addEventListener("change", async () => {
  const attempt = ++loadAttempt;
  const file = pilotInput.files[0];
  if (!file) return;
  try {
    const raw = await file.text();
    if (attempt !== loadAttempt) return;
    const loaded = validatePilot(JSON.parse(raw));
    pilot = loaded;
    ratings = new Map();
    position = 0;
    setStatus("save-status", "");
    if (!restoreProgress()) {
      setStatus("save-status", "No se pudo recuperar el progreso guardado en este navegador.", true);
    }
    setStatus("load-status", Object.keys(pilot.tracks).length + " letras cargadas.");
    workspace.hidden = false;
    showPair();
  } catch (error) {
    if (attempt !== loadAttempt) return;
    const message = error instanceof SyntaxError ? "El archivo no contiene JSON válido." : error.message;
    setStatus("load-status", message, true);
    pilotInput.value = "";
  }
});

previous.addEventListener("click", () => navigate(position - 1));
next.addEventListener("click", () => navigate(position + 1));
nextPending.addEventListener("click", () => navigate(pendingPosition()));
notes.addEventListener("input", () => updateRating("notes", notes.value));
exportButton.addEventListener("click", () => {
  const finished = pilot.pairs.flatMap((pair) => {
    const rating = ratings.get(pairKey(pair));
    return complete(rating) ? [{ query_id: pair.query_id, candidate_id: pair.candidate_id, ...rating }] : [];
  });
  const payload = JSON.stringify({ pilot_id: pilot.pilot_id, ratings: finished }, null, 2);
  const url = URL.createObjectURL(new Blob([payload], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "valoraciones-sonora.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
