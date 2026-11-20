'use strict';

const byId = id => document.getElementById(id);
const audio = byId('audio');
const queue = [];
let position = -1, upcoming = null, queueRequest, searchRequest, lyricRequest;
const ratingForm = byId('player-rating');
const ratingFields = ratingForm.querySelector('fieldset');
const ratingAxes = ['emotion', 'theme', 'music_vibe'];
const ratingWrites = new Map();
let ratingRequest, ratingContext;
for (const axis of ratingAxes) {
 const select = ratingForm.elements.namedItem(axis);
 select.add(new Option('Sin calificar', ''));
 for (let grade = 0; grade <= 5; grade += 0.5) select.add(new Option(grade.toLocaleString('es'), String(grade)));
}
let saved = [];
let savedReady = false;

async function get(path, signal) {
 const response = await fetch('/api/v1/songs' + path, {signal});
 const data = await response.json();
 if (!response.ok) throw new Error(data.detail || 'El catálogo no está disponible.');
 return data;
}

function browserId() {
 const key = 'sonora-rater-id';
 const stored = localStorage.getItem(key);
 if (stored && /^[0-9a-f]{32}$/.test(stored)) return stored;
 const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
 localStorage.setItem(key, id);
 return id;
}

async function ratingApi(suffix, options) {
 const response = await fetch('/api/v1/song-ratings' + suffix, options);
 if (!response.ok) throw new Error('Calificación no disponible');
 return (await response.json()).rating;
}

async function loadRating() {
 ratingRequest?.abort();
 const controller = new AbortController();
 ratingRequest = controller;
 ratingContext = null;
 const current = queue[position];
 const panel = byId('player-feedback');
 panel.hidden = !upcoming || current.track_id === upcoming.track_id;
 ratingForm.reset();
 ratingFields.disabled = true;
 if (panel.hidden) return;
 byId('feedback-pair').textContent = current.title + ' → ' + upcoming.title;
 const status = byId('feedback-status');
 status.textContent = 'Buscando tu calificación…';
 try {
  const pair = {query_id: current.track_id, candidate_id: upcoming.track_id, rater_id: browserId()};
  const key = new URLSearchParams(pair).toString();
  await ratingWrites.get(key)?.catch(() => {});
  const rating = await ratingApi('?' + key, {signal: controller.signal});
  if (controller.signal.aborted) return;
  ratingContext = {pair, key, rank: upcoming.rank || 0};
  for (const axis of ratingAxes) ratingForm.elements.namedItem(axis).value = rating?.[axis] ?? '';
  ratingFields.disabled = false;
  status.textContent = rating ? 'Tu calificación guardada.' : '';
 } catch {
  if (!controller.signal.aborted) status.textContent = 'No se pudo cargar tu calificación.';
 }
}

ratingForm.addEventListener('submit', async event => {
 event.preventDefault();
 const context = ratingContext;
 if (!context || ratingFields.disabled) return;
 const scores = Object.fromEntries(ratingAxes.map(axis => {
  const value = ratingForm.elements.namedItem(axis).value;
  return [axis, value === '' ? null : Number(value)];
 }));
 const status = byId('feedback-status');
 if (Object.values(scores).every(value => value === null)) {
  status.textContent = 'Califica al menos una escala.';
  return;
 }
 ratingFields.disabled = true;
 status.textContent = 'Guardando…';
 const write = ratingApi('', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({...context.pair, rank: context.rank, ...scores}),
 });
 ratingWrites.set(context.key, write);
 try {
  await write;
  if (context === ratingContext) status.textContent = 'Calificación guardada.';
 } catch {
  if (context === ratingContext) status.textContent = 'No se pudo guardar. Inténtalo de nuevo.';
 } finally {
  ratingWrites.delete(context.key);
  if (context === ratingContext) ratingFields.disabled = false;
 }
});

function renderTracks(list, tracks) {
 list.replaceChildren(...tracks.map(track => {
  const item = document.createElement('li');
  const button = document.createElement('button');
  const title = document.createElement('strong');
  const artist = document.createElement('span');
  title.textContent = track.title;
  artist.textContent = track.artist || 'Artista desconocido';
  button.append(title, artist);
  button.addEventListener('click', () => {
   queue.splice(position + 1, queue.length, track);
   position++;
   selectTrack();
   byId('player-title').scrollIntoView({block: 'nearest'});
  });
  item.append(button);
  return item;
 }));
}

async function search() {
 searchRequest?.abort();
 const query = byId('query').value.trim();
 if (!query) return;
 const controller = new AbortController();
 searchRequest = controller;
 const status = byId('search-status');
 status.textContent = 'Buscando…';
 renderTracks(byId('results'), []);
 try {
  const data = await get('?' + new URLSearchParams({q: query}), controller.signal);
  if (controller.signal.aborted) return;
  renderTracks(byId('results'), data.items);
  status.textContent = data.items.length ? '' : 'Sin resultados. Prueba con el título o el artista.';
 } catch {
  if (!controller.signal.aborted) status.textContent = 'No se pudo buscar. Abre SONORA desde su servidor local e inténtalo de nuevo.';
 }
}

function weightedChoice(tracks) {
 let draw = Math.random() * (tracks.length * (tracks.length + 1) / 2);
 const index = tracks.findIndex((_, rank) => (draw -= tracks.length - rank) < 0);
 return index < 0 ? null : {...tracks[index], rank: index + 1};
}

function renderUpcoming() {
 byId('next').disabled = !upcoming;
 byId('up-next').textContent = upcoming ? 'Siguiente · ' + upcoming.title + ' — ' + upcoming.artist : 'Buscando la siguiente canción…';
 if (!byId('comparison').hidden) showLyrics();
 loadRating();
}

async function prepareUpcoming() {
 queueRequest?.abort();
 const controller = new AbortController();
 queueRequest = controller;
 upcoming = queue[position + 1] || null;
 renderUpcoming();
 if (upcoming) return;
 const track = queue[position];
 try {
  const {items} = await get('/' + track.track_id + '/related', controller.signal);
  if (controller.signal.aborted) return;
  upcoming = weightedChoice(items);
  renderUpcoming();
  if (!upcoming) byId('up-next').textContent = 'No hay una siguiente canción disponible.';
  else if (audio.ended) advance();
 } catch {
  if (!controller.signal.aborted) byId('up-next').textContent = 'No se pudo preparar la siguiente canción.';
 }
}

function play() {
 audio.play().catch(error => {
  if (error.name !== 'AbortError') byId('player-status').textContent = 'Pulsa Reproducir para iniciar la canción.';
 });
}

function selectTrack() {
 const track = queue[position];
 byId('player-title').textContent = track.title;
 byId('artist').textContent = track.artist;
 byId('license').textContent = track.license;
 byId('toggle').disabled = !track.audio_url;
 byId('save').disabled = !savedReady;
 byId('lyrics').disabled = false;
 byId('previous').disabled = position < 1;
 byId('player-status').textContent = track.audio_url ? '' : 'Letra disponible · sin audio';
 audio.pause();
 if (track.audio_url) {
  audio.src = track.audio_url;
 } else {
  audio.removeAttribute('src');
  audio.load();
  byId('comparison').hidden = false;
  byId('lyrics').setAttribute('aria-expanded', 'true');
 }
 updateTimeline();
 renderSaved();
 prepareUpcoming();
 if (track.audio_url) play();
}

function advance() {
 if (!upcoming) return;
 if (!queue[position + 1]) queue.push(upcoming);
 position++;
 selectTrack();
}

function renderSaved() {
 renderTracks(byId('saved-list'), saved);
 byId('saved-empty').hidden = saved.length > 0;
 const isSaved = saved.some(track => track.track_id === queue[position]?.track_id);
 byId('save').textContent = isSaved ? '♥ Guardada' : '♡ Guardar';
 byId('save').setAttribute('aria-pressed', String(isSaved));
}

async function showLyrics() {
 lyricRequest?.abort();
 const controller = new AbortController();
 lyricRequest = controller;
 const columns = byId('lyric-columns');
 columns.replaceChildren();
 await Promise.all([queue[position], upcoming].map(async (track, index) => {
  const panel = document.createElement('article');
  const heading = document.createElement('h3');
  const role = document.createElement('small');
  const text = document.createElement('p');
  role.textContent = index ? 'SIGUIENTE' : 'ACTUAL';
  heading.textContent = track ? track.title + (track.artist ? ' — ' + track.artist : '') : 'Por determinar';
  text.textContent = track ? 'Cargando letra…' : 'Aquí verás la letra de la siguiente canción.';
  text.tabIndex = 0;
  panel.append(role, heading, text);
  columns.append(panel);
  if (!track) return;
  try {
   const lyric = await get('/' + track.track_id + '/lyrics', controller.signal);
   text.textContent = lyric.text || 'Letra no disponible.';
  } catch (error) {
   if (!controller.signal.aborted) text.textContent = error.message;
  }
 }));
}

function timeLabel(seconds) {
 const rounded = Math.floor(seconds);
 return Math.floor(rounded / 60) + ':' + String(rounded % 60).padStart(2, '0');
}

function updateTimeline() {
 const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
 const seek = byId('seek');
 seek.disabled = !duration;
 seek.max = duration;
 seek.value = audio.currentTime || 0;
 byId('elapsed').textContent = timeLabel(audio.currentTime || 0);
 byId('duration').textContent = timeLabel(duration);
}

byId('search').addEventListener('submit', event => {event.preventDefault(); search();});
byId('example').addEventListener('click', () => {byId('query').value = 'Freeway Kurt Vile'; search();});
byId('previous').addEventListener('click', () => {if (position > 0) {position--; selectTrack();}});
byId('toggle').addEventListener('click', () => {if (audio.paused) play(); else audio.pause();});
byId('next').addEventListener('click', advance);
byId('seek').addEventListener('input', event => {audio.currentTime = Number(event.target.value);});
byId('save').addEventListener('click', () => {
 const track = queue[position];
 const index = saved.findIndex(item => item.track_id === track.track_id);
 if (index === -1) saved.push(track);
 else saved.splice(index, 1);
 try {localStorage.setItem('sonora-saved-music', JSON.stringify(saved));}
 catch {byId('player-status').textContent = 'El navegador solo permite guardar durante esta sesión.';}
 renderSaved();
});
byId('lyrics').addEventListener('click', () => {
 const panel = byId('comparison');
 panel.hidden = !panel.hidden;
 byId('lyrics').setAttribute('aria-expanded', String(!panel.hidden));
 if (!panel.hidden) {
  showLyrics();
  panel.scrollIntoView({block: 'nearest'});
 } else lyricRequest?.abort();
});
audio.addEventListener('play', () => {byId('toggle').textContent = '⏸ Pausar';});
audio.addEventListener('pause', () => {byId('toggle').textContent = '▶ Reproducir';});
audio.addEventListener('ended', advance);
audio.addEventListener('error', () => {byId('player-status').textContent = 'No se pudo reproducir esta canción.';});
for (const event of ['timeupdate', 'loadedmetadata', 'emptied']) audio.addEventListener(event, updateTimeline);
renderSaved();

async function restoreSaved() {
 try {
  const stored = JSON.parse(localStorage.getItem('sonora-saved-music') || '[]');
  if (!Array.isArray(stored)) return;
  const checked = await Promise.allSettled(stored.filter(track => track?.track_id)
   .map(track => get('/' + encodeURIComponent(track.track_id))));
  const available = checked.filter(result => result.status === 'fulfilled').map(result => result.value);
  saved = [...new Map([...available, ...saved].map(track => [track.track_id, track])).values()];
  renderSaved();
 } catch {} finally {
  savedReady = true;
  if (position >= 0) byId('save').disabled = false;
 }
}
restoreSaved();

async function openSelectedTrack() {
 const id = new URLSearchParams(location.search).get('cancion');
 if (!id) return;
 const status = byId('player-status');
 status.textContent = 'Cargando canción…';
 try {
  const track = await get('/' + encodeURIComponent(id));
  if (position >= 0) return;
  queue.push(track);
  position = 0;
  selectTrack();
 } catch {
  if (position < 0) status.textContent = 'No se pudo abrir la canción. Vuelve al portal para buscar otra.';
 }
}
openSelectedTrack();
