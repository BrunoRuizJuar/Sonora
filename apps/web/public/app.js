'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let cache = new Map(), results = [], seed = null, page = 'discover', pending = false;
let saved = [], toastTimer, lastRequest = null, searchNumber = 0, searchTimer;
let comparisonController = null, comparisonNumber = 0;
let ratingContext = null;
const ratingWrites = new Map();
const lyricCache = new Map();
try { saved = JSON.parse(localStorage.getItem('sonora-text-saved') || '[]'); if(!Array.isArray(saved)) saved=[]; } catch {}
saved = saved.filter(song => song && typeof song.id === 'string');
saved.forEach(s => cache.set(s.id, s));
function notify(message) { clearTimeout(toastTimer); $('#toast').textContent=message; $('#toast').hidden=false; toastTimer=setTimeout(()=>$('#toast').hidden=true,4000); }
async function api(path, body, signal) {
 const response = await fetch('/api/v1'+path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal} : {signal});
 const data = await response.json();
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:response.status===422?'Revisa los parámetros de la consulta.':data.reason||`Error ${response.status}`);
 return data;
}
function status(title, copy) { $('#empty-title').textContent=title; $('#empty-copy').textContent=copy; $('#empty-state').hidden=false; $('#song-grid').hidden=true; }
function reason(song) { return song.score===undefined?'Letra del catálogo textual; audio no disponible.':`${song.strategy==='tfidf'?'Vocabulario TF-IDF':'Afinidad SGNS'} · coseno ${song.score.toFixed(4)}. ${song.shared_terms?.length?'Términos compartidos: '+song.shared_terms.join(', ')+'.':'Sin términos compartidos.'}`; }
function render() {
 const list=page==='saved'?saved:results;
 $('#saved-count').textContent=saved.length;
 $$('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
 $('#refresh-route').hidden=page==='saved'||!lastRequest;
 $('#recommendation-title').textContent=page==='saved'?'Canciones guardadas':seed?'A partir de '+seed.title:'Explora las letras';
 $('#recommendation-subtitle').textContent=page==='saved'?'Guardadas en este navegador.':seed?seed.artist:'Busca título y artista, o escribe una consulta en inglés.';
 $('#song-grid').innerHTML=list.map(s=>`<article class="song-card"><div class="cover-wrap" style="display:grid;place-items:center;background:var(--surface)"><img src="assets/brand/cactus-sonora.svg" alt="Símbolo de SONORA; sin portada disponible" style="object-fit:contain;width:35%;height:65%"><span class="cover-corner">CATÁLOGO TEXTUAL</span></div><button class="song-link" data-detail="${escapeHTML(s.id)}">${escapeHTML(s.title)}</button><p class="song-artist">${escapeHTML(s.artist)}</p><button class="save-song" data-save="${escapeHTML(s.id)}" aria-label="Guardar ${escapeHTML(s.title)}" aria-pressed="${saved.some(x=>x.id===s.id)}"><svg><use href="#i-heart"/></svg></button><p class="song-reason">${escapeHTML(reason(s))}</p><div class="song-language">CORPUS INGLÉS · LETRAS</div></article>`).join('');
 $$('#song-grid .song-card').forEach((card,i)=>{const button=document.createElement('button');button.type='button';button.className='compare-lyrics';button.dataset.compare=list[i].id;button.textContent=lastRequest?(canRate(list[i].id)?'Comparar y calificar':'Comparar letras'):'Elige una canción de partida para comparar';button.disabled=!lastRequest;card.append(button);});
 $('#song-grid').hidden=!list.length;
 $('#empty-state').hidden=!!list.length;
 if(!list.length) status(pending?'Buscando afinidades…':page==='saved'?'Tu mapa empieza aquí':'Sin resultados',pending?'Consulta exacta sobre el catálogo completo.':page==='saved'?'Guarda una canción para volver a encontrarla.':'Selecciona una canción o prueba otra consulta.');
}
async function recommend(input) {
 if(pending) return;
 closeLyrics();
 pending=true; results=[]; page='discover'; lastRequest=input; render();
 $('#refresh-route').disabled=true;
 try {
  const request={...input,mode:'lyrics',strategy:$('#text-strategy').value,top_k:10,max_per_artist:$('#limit-artists').checked?1:null};
  const data=await api('/recommendations?require_lyrics=true',request);
  results=data.items.map(s=>({...s,strategy:data.strategy,space_id:data.space_id}));
  recommendationRelease = data.release_id;
  results.forEach(s=>cache.set(s.id,s));
  $('#version-note').textContent=`${data.catalog_version} · ${data.space_id.slice(0,12)} · ${data.elapsed_seconds.toFixed(2)} s. Afinidad numérica; no garantiza el mismo tema.`;
  pending=false; render();
  if(!results.length) status('Sin afinidades disponibles','Prueba otro texto o estrategia. No se añaden canciones de ejemplo.');
 } catch(error) { pending=false; render(); status('No pudimos recomendar',error.message); }
 finally { $('#refresh-route').disabled=false; }
}
async function selectSeed(id) {
 if(pending) return;
 try {
  seed=await api('/songs/'+encodeURIComponent(id)); cache.set(id,seed);
  $('#song-search').value=''; $('#search-results').hidden=true; $('#song-search').setAttribute('aria-expanded','false');
  await recommend({track_id:id});
 } catch(error) { status('No pudimos abrir la canción',error.message); }
}
async function showResults() {
 const number=++searchNumber, q=$('#song-search').value.trim();
 if(!q) { $('#search-results').hidden=true; return; }
 $('#search-results').hidden=false; $('#song-search').setAttribute('aria-expanded','true'); $('#search-results').innerHTML='<p>Buscando título y artista…</p>';
 try {
  const data=await api('/songs?q='+encodeURIComponent(q));
  if(number!==searchNumber || q!==$('#song-search').value.trim()) return;
  data.items.forEach(s=>cache.set(s.id,s));
  $('#search-results').innerHTML=data.items.length?data.items.map(s=>`<button type="button" data-seed="${escapeHTML(s.id)}"><span><b>${escapeHTML(s.title)}</b><small>${escapeHTML(s.artist)} · ${escapeHTML(s.id)}</small></span><svg><use href="#i-arrow"/></svg></button>`).join(''):'<p>No encontramos ese título/artista. La consulta por significado se escribe en el campo de texto libre.</p>';
 } catch(error) { if(number===searchNumber) $('#search-results').textContent=error.message; }
}
function toggleSave(id) {
 const s=cache.get(id); if(!s) return;
 saved=saved.some(x=>x.id===id)?saved.filter(x=>x.id!==id):[...saved,s];
 try { localStorage.setItem('sonora-text-saved',JSON.stringify(saved)); } catch { notify('Guardado sólo durante esta visita.'); }
 render();
}
function showDetail(id) {
 const s=cache.get(id); if(!s) return;
 $('#dialog-content').innerHTML=`<div class="dialog-kicker">CATÁLOGO TEXTUAL · SIN AUDIO</div><h2 class="dialog-title">${escapeHTML(s.title)}</h2><p class="dialog-artist">${escapeHTML(s.artist)}</p><p class="dialog-reason">${escapeHTML(reason(s))}</p><p class="dialog-note">${escapeHTML(s.id)} · ${escapeHTML(s.split)}. Identifica una letra canónica, sin correspondencia verificada a grabaciones. ${escapeHTML(s.space_id||'')}</p><button class="primary-button" data-dialog-seed="${escapeHTML(s.id)}">Partir de esta canción</button>`;
 if(lastRequest){const button=document.createElement('button');button.type='button';button.className='compare-lyrics';button.textContent='Ver letras lado a lado ↗';button.addEventListener('click',()=>{$('#song-dialog').close();compareLyrics(id);});$('#dialog-content').append(button);}
 $('#song-dialog').showModal();
}
function closeLyrics() {
 comparisonNumber++; comparisonController?.abort(); comparisonController=null;
 ratingContext=null;
 ratingForm.hidden=true;
 $('#lyrics-comparison').hidden=true;
 for(const side of ['origin','selected']){$(`#lyrics-${side}-text`).textContent='';$(`#lyrics-${side}-status`).textContent='';}
}
async function loadLyric(id,signal) {
 if(lyricCache.has(id))return lyricCache.get(id);
 const lyric=await api('/tracks/'+encodeURIComponent(id)+'/lyrics',undefined,signal);
 if(lyricCache.size>=8)lyricCache.delete(lyricCache.keys().next().value);
 lyricCache.set(id,lyric);return lyric;
}
async function compareLyrics(id) {
 if(!lastRequest || pending)return;
 const selected=cache.get(id);if(!selected)return;
 closeLyrics();comparisonController=new AbortController();
 const number=comparisonNumber, signal=comparisonController.signal;
 const origin=lastRequest.track_id?cache.get(lastRequest.track_id):null;
 $('#lyrics-origin-label').textContent=origin?'CANCIÓN DE PARTIDA':'TEXTO DE PARTIDA';
 $('#lyrics-origin-title').textContent=origin?.title||'Tu consulta';
 $('#lyrics-origin-artist').textContent=origin?.artist||'Texto que escribiste para buscar afinidad';
 $('#lyrics-selected-title').textContent=selected.title;$('#lyrics-selected-artist').textContent=selected.artist;
 $('#lyrics-comparison').hidden=false;
 if(canRate(id)) loadRating(id, number, signal);
 $('#lyrics-comparison-title').focus({preventScroll:true});
 $('#lyrics-comparison').scrollIntoView({behavior:'smooth',block:'start'});
 async function fill(side,identifier,text) {
  const content=$(`#lyrics-${side}-text`), status=$(`#lyrics-${side}-status`);
  status.textContent='Cargando letra…';content.setAttribute('aria-busy','true');
  try {
   const lyric=identifier?await loadLyric(identifier,signal):{text,view:'query'};
   if(number!==comparisonNumber)return;
   content.textContent=lyric.text;content.scrollTop=0;
   status.textContent=lyric.view==='query'?'Consulta original':'Letra original del corpus';
  } catch(error) {
   if(number!==comparisonNumber || error.name==='AbortError')return;
   status.textContent='No se pudo cargar la letra: '+error.message;
  } finally {if(number===comparisonNumber)content.setAttribute('aria-busy','false');}
 }
 await Promise.allSettled([fill('origin',lastRequest.track_id,lastRequest.text),fill('selected',id)]);
}

let recommendationRelease = null;
const ratingForm = $('#recommendation-rating');
const ratingFields = $('fieldset', ratingForm);
const ratingStatus = $('#rating-status');
const ratingAxes = ['emotion','theme','music_vibe'];
for(const axis of ratingAxes) {
 const select = ratingForm.elements.namedItem(axis);
 select.add(new Option('Sin calificar', ''));
 for(let grade=0;grade<=5;grade+=0.5) select.add(new Option(grade.toLocaleString('es'), String(grade)));
}
function canRate(id) {
 return !!(lastRequest?.track_id && recommendationRelease && results.some(song=>song.id===id));
}
function getRaterId() {
 const stored = localStorage.getItem('sonora-rater-id');
 if(stored && /^[0-9a-f]{32}$/.test(stored)) return stored;
 const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte=>byte.toString(16).padStart(2,'0')).join('');
 localStorage.setItem('sonora-rater-id', id);
 return id;
}
async function loadRating(id, number, signal) {
 ratingForm.reset();
 ratingForm.hidden=false;
 ratingFields.disabled=true;
 ratingStatus.textContent='Buscando tu calificación…';
 try {
  const key = {release_id:recommendationRelease, query_id:lastRequest.track_id, candidate_id:id, rater_id:getRaterId()};
  const index = results.findIndex(song=>song.id===id);
  const lookup = '/recommendations/ratings?'+new URLSearchParams(key);
  const context = {lookup, rating:{...key, strategy:results[index].strategy, rank:index+1}};
  await ratingWrites.get(lookup)?.catch(()=>{});
  const {rating} = await api(lookup,undefined,signal);
  if(number!==comparisonNumber) return;
  for(const axis of ratingAxes) ratingForm.elements.namedItem(axis).value=rating?.[axis] ?? '';
  ratingContext=context;
  ratingFields.disabled=false;
  ratingStatus.textContent=rating?'Tu calificación guardada. Puedes actualizarla.':'';
 } catch(error) {
  if(number===comparisonNumber) ratingStatus.textContent='No se pudo cargar la calificación. Vuelve a abrir la comparación para reintentar.';
 }
}
ratingForm.addEventListener('submit', async event=>{
 event.preventDefault();
 if(!ratingContext || ratingFields.disabled) return;
 const context = ratingContext;
 const values = Object.fromEntries(ratingAxes.map(axis=>{
  const value = ratingForm.elements.namedItem(axis).value;
  return [axis, value==='' ? null : Number(value)];
 }));
 if(values.theme===null && values.emotion===null) {
  ratingStatus.textContent='Califica al menos una escala.';
  return;
 }
 ratingFields.disabled=true;
 ratingStatus.textContent='Guardando…';
 const write = api('/recommendations/ratings',{...context.rating,...values});
 ratingWrites.set(context.lookup,write);
 try {
  await write;
  if(context===ratingContext) ratingStatus.textContent='Calificación guardada.';
 } catch(error) {
  if(context===ratingContext) ratingStatus.textContent=error.message;
 } finally {
  if(ratingWrites.get(context.lookup)===write) ratingWrites.delete(context.lookup);
  if(context===ratingContext) ratingFields.disabled=false;
 }
});
// Keep the approved visual shell, direction selection and responsive layout.
const themes = {
 ocaso:{number:'01',title:'Radio Ocaso',copy:'Una estación musical al caer el sol. La ruta más cinematográfica: portadas protagonistas, luz cálida, fondos profundos y la comodidad de una app musical cotidiana.',type:'Rye en la marca y los titulares, con Open Sans en los controles.',texture:'Café profundo, cuero, crema y naranja quemado. Grabado del desierto con cactus en silueta.',colors:['#1B1410','#2B2019','#F2E2C4','#D97732','#A94732']},
 archivo:{number:'02',title:'Archivo del Desierto',copy:'Una colección de hallazgos musicales, como una caja de discos junto a un mapa antiguo. El espíritu western se acerca a la imprenta y al grabado, con una composición editorial más marcada.',type:'Rye en la marca y los titulares. Open Sans en búsqueda, controles y tarjetas. Mono en pequeñas etiquetas, como en un catálogo impreso.',texture:'Base tabaco y portadas sobre crema envejecida. Rojo óxido como tinta, bordes rectos, filetes dobles y textura de papel muy sutil.',colors:['#261B15','#E8D6B5','#382318','#A94732','#D58A59']},
 cobre:{number:'03',title:'Frecuencia Cobre',copy:'Una estación de radio analógica en medio del desierto. La ruta más sobria: mapas topográficos, señales, escalas de sintonía y mucho espacio para que respire la música.',type:'Rye en la marca y los titulares, Open Sans en los controles y Mono en las coordenadas.',texture:'Sepia casi negro, cobre y crema. Contornos finos, tramas topográficas y superficies mate; menos ornamento y una señal visual más precisa.',colors:['#191513','#25201D','#F0E3CE','#DB8A58','#AB4D3A']}
};
function themeFromUrl(){const v=new URL(location.href).searchParams.get('direccion');return themes[v]?v:'ocaso';}
function setTheme(name){
 document.body.dataset.theme=name;
 const t=themes[name];
 $$('[data-direction]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.direction===name)));
 $('#brand-mark').src='assets/brand/cactus-sonora.svg';
 $('#download-logo').href='assets/brand/cactus-sonora.svg';
 $('#empty-state img').src='assets/brand/cactus-sonora.svg';
 $('.brand').href=`?direccion=${name}`;
 $('link[rel=icon]').href='assets/brand/cactus-sonora.svg';
 $('#brief-number').textContent=t.number;$('#brief-title').textContent=t.title;$('#brief-copy').textContent=t.copy;$('#brief-type').textContent=t.type;$('#brief-texture').textContent=t.texture;
 $('#swatches').innerHTML=t.colors.map(c=>`<span class="swatch"><i style="background:${c}"></i>${c}</span>`).join('');
 const u=new URL(location.href);u.searchParams.set('direccion',name);history.replaceState({},'',u);
 document.title=`SONORA · ${t.title}`;
}
setTheme(themeFromUrl());
$('.brief-toggle').addEventListener('click',()=>{const panel=$('#design-brief');panel.hidden=!panel.hidden;$('.brief-toggle').setAttribute('aria-expanded',String(!panel.hidden));});
$$('[data-mode]').forEach(b=>{const available=b.dataset.mode==='lyrics';b.disabled=!available;b.title=available?'Recomendación por letra':'No disponible: falta integración de audio';b.classList.toggle('selected',available);b.setAttribute('aria-pressed',String(available));});
$('#mix-block').hidden=true;
$('#mode-explanation').textContent='Modelo inglés. SGNS muestra afinidad del embedding; TF-IDF busca vocabulario compartido. Sin traducción ni audio.';
$('#filter-toggle').addEventListener('click',()=>{const f=$('#filters');f.hidden=!f.hidden;$('#filter-toggle').setAttribute('aria-expanded',String(!f.hidden));});
$('#exclude-covers').checked=false; $('#exclude-covers').disabled=true; $('#exclude-covers').parentElement.title='Covers musicales no verificados';
$('#exploration').disabled=true; $('#explore-value').textContent='No disponible';
$('#language').innerHTML='<option>Corpus inglés</option>'; $('#language').disabled=true;
$('#filter-count').textContent='1';
$('#limit-artists').addEventListener('change',()=>{ $('#filter-count').textContent=$('#limit-artists').checked?'1':'0'; if(lastRequest)recommend(lastRequest); });
$('#song-search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(showResults,300);});
$('#song-search').addEventListener('keydown',e=>{if(e.key==='Escape')$('#search-results').hidden=true;if(e.key==='ArrowDown'){$('#search-results button')?.focus();e.preventDefault();}});
$('#search-form').addEventListener('submit',e=>{e.preventDefault();showResults();});
$('#search-results').addEventListener('click',e=>{const b=e.target.closest('[data-seed]');if(b)selectSeed(b.dataset.seed);});
$('#song-grid').addEventListener('click',e=>{const b=e.target.closest('[data-save],[data-detail],[data-compare]');if(!b)return;if(b.dataset.compare){compareLyrics(b.dataset.compare);return;}b.dataset.save?toggleSave(b.dataset.save):showDetail(b.dataset.detail);});
$('#close-lyrics').addEventListener('click',()=>{closeLyrics();$('#recommendation-title').scrollIntoView({block:'start'});});
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.page==='search'){$('#song-search').focus();return;}page=b.dataset.page;render();}));
$$('[data-query]').forEach(b=>{b.addEventListener('click',()=>{$('#song-search').value=b.dataset.query;showResults();$('#song-search').focus();});});
$('#refresh-route').textContent='Recalcular la ruta';
$('#refresh-route').addEventListener('click',()=>lastRequest&&recommend(lastRequest));
$('#back-discover').addEventListener('click',()=>{page='discover';render();});
$('.dialog-close').addEventListener('click',()=>$('#song-dialog').close());
$('#song-dialog').addEventListener('click',e=>{if(e.target===$('#song-dialog'))$('#song-dialog').close();const b=e.target.closest('[data-dialog-seed]');if(b){$('#song-dialog').close();selectSeed(b.dataset.dialogSeed);}});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#song-search').focus();}});
$('#free-text-form').addEventListener('submit',e=>{e.preventDefault();if(pending)return;seed={title:'tu texto',artist:'Consulta en inglés'};recommend({text:$('#free-text').value});});
$('#text-strategy').addEventListener('change',()=>lastRequest&&recommend(lastRequest));

const fmaForm = $('#fma-search');
const fmaQuery = $('#fma-query');
const fmaResults = $('#fma-results');
const fmaStatus = $('#fma-status');
let fmaSearchController;

async function searchFma() {
 fmaSearchController?.abort();
 const query = fmaQuery.value.trim();
 if (location.protocol === 'file:') {
  fmaStatus.textContent = 'La búsqueda y la reproducción requieren el servidor de SONORA.';
  $('#fma-local-link').hidden = false;
  return;
 }
 if (!query) {
  fmaResults.replaceChildren();
  fmaStatus.textContent = 'Escribe un título o un artista.';
  fmaQuery.focus();
  return;
 }
 const controller = new AbortController();
 fmaSearchController = controller;
 fmaStatus.textContent = 'Buscando canciones…';
 fmaResults.replaceChildren();
 try {
  const params = new URLSearchParams({q:query, limit:12});
  const data = await api('/songs?' + params, null, controller.signal);
  if (controller.signal.aborted) return;
  if (!Array.isArray(data.items)) throw new Error('Respuesta de catálogo no disponible');
  fmaStatus.textContent = data.items.length
   ? `${data.items.length} ${data.items.length === 1 ? 'canción encontrada' : 'canciones mostradas'}`
   : 'No encontramos canciones. Prueba con solo el título o el artista.';
  fmaResults.innerHTML = data.items.map(track => `
   <article class="fma-track">
    <a href="/reproductor.html?cancion=${encodeURIComponent(track.track_id)}">
     <h3>${escapeHTML(track.title)}</h3><p>${escapeHTML(track.artist || 'Artista sin registrar')}</p>
     <span>${track.audio_url ? '▶ Abrir en el reproductor' : 'Leer letra'}</span>
    </a>
   </article>`).join('');
 } catch {
  if (!controller.signal.aborted) {
   fmaStatus.textContent = 'El catálogo de música no responde. Vuelve a intentar la búsqueda.';
  }
 }
}

$('#fma-link').addEventListener('click', () => {
 fmaQuery.focus({preventScroll:true});
});
$('#fma-example').addEventListener('click', () => {
 fmaQuery.value = 'Freeway Kurt Vile';
 searchFma();
});
fmaForm.addEventListener('submit', event => {
 event.preventDefault();
 searchFma();
});
if (location.protocol === 'file:') searchFma();

render();
Promise.allSettled(saved.map(song => api('/songs/'+encodeURIComponent(song.id)))).then(checked => {
 const available = new Set(checked.filter(result => result.status === 'fulfilled').map(result => result.value.id));
 saved = saved.filter(song => available.has(song.id));
 render();
});
api('/catalog/stats').then(data=>{$('.catalog-label').textContent=`${data.rows.toLocaleString('es')} letras · modelo inglés`;$('#version-note').textContent=`${data.version} · ${data.space_id.slice(0,12)}. Catálogo exploratorio completo; sin evaluación de relevancia.`;}).catch(error=>status('Catálogo no disponible',error.message));
