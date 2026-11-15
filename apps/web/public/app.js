'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const themes = {
 ocaso:{number:'01',title:'Radio Ocaso',copy:'Una estación musical al caer el sol. La ruta más cinematográfica: portadas protagonistas, luz cálida, fondos profundos y la comodidad de una app musical cotidiana.',type:'Open Sans en títulos y controles. Noto Serif Display en SONORA y detalles editoriales. El carácter western aparece en la marca, sin dificultar la lectura.',texture:'Café profundo, cuero, crema y naranja quemado. Fotografía original del desierto, grano de película y sombras suaves.',colors:['#1B1410','#2B2019','#F2E2C4','#D97732','#A94732']},
 archivo:{number:'02',title:'Archivo del Desierto',copy:'Una colección de hallazgos musicales, como una caja de discos junto a un mapa antiguo. El espíritu western se acerca a la imprenta y al grabado, con una composición editorial más marcada.',type:'Noto Serif Display en titulares y wordmark. Open Sans en búsqueda, controles y tarjetas. Mono en pequeñas etiquetas, como en un catálogo impreso.',texture:'Base tabaco y portadas sobre crema envejecida. Rojo óxido como tinta, bordes rectos, filetes dobles y textura de papel muy sutil.',colors:['#261B15','#E8D6B5','#382318','#A94732','#D58A59']},
 cobre:{number:'03',title:'Frecuencia Cobre',copy:'Una estación de radio analógica en medio del desierto. La ruta más sobria: mapas topográficos, señales, escalas de sintonía y mucho espacio para que respire la música.',type:'Open Sans en marca, títulos y controles. Mono para coordenadas y etiquetas. La identidad western se expresa con el cactus, el paisaje y el color.',texture:'Sepia casi negro, cobre y crema. Contornos finos, tramas topográficas y superficies mate; menos ornamento y una señal visual más precisa.',colors:['#191513','#25201D','#F0E3CE','#DB8A58','#AB4D3A']}
};
const songs = [
 {id:'raiz',title:'Hasta la Raíz',artist:'Natalia Lafourcade',language:'es',cover:'raiz',lyrics:'Memoria, amor y pertenencia como hilo conductor.',music:'Instrumentación orgánica y una voz cercana.',mixed:'Raíz emocional y una instrumentación cálida.'},
 {id:'brillas',title:'Brillas',artist:'León Larregui',language:'es',cover:'brillas',lyrics:'Imágenes de amor y luz, con un tono íntimo.',music:'Texturas suaves, pulso relajado y voz cálida.',mixed:'Calidez sonora y letras que hablan del amor.'},
 {id:'eres',title:'Eres',artist:'Café Tacvba',language:'es',cover:'eres',lyrics:'Una declaración de amor directa y luminosa.',music:'Guitarras suaves y una melodía que abraza.',mixed:'Romance cercano y una melodía orgánica.'},
 {id:'san-lucas',title:'San Lucas',artist:'Kevin Kaarl',language:'es',cover:'san-lucas',lyrics:'Nostalgia, afecto y ganas de partir juntos.',music:'Guitarra acústica y una interpretación íntima.',mixed:'Nostalgia en la letra y guitarra íntima.'},
 {id:'bloom',title:'Bloom',artist:'The Paper Kites',language:'en',cover:'bloom',lyrics:'Cercanía y ternura contadas con delicadeza.',music:'Folk acústico, arreglos delicados y voz suave.',mixed:'Folk cálido y una historia de cercanía.'}
];
let storageAvailable=true;let saved=[];
try{saved=JSON.parse(localStorage.getItem('sonora-visual-saved')||'[]');if(!Array.isArray(saved)) saved=[];}catch{storageAvailable=false;}
let mode='mixed',seed=songs[0],page='discover',alternate=false,toastTimer;
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
function notify(message){clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,3200);}
function reason(song){if(mode==='mixed'){const weight=100-(+$('#mix-range').value);return weight>=75?song.lyrics:weight<=25?song.music:song.mixed;}return song[mode];}
function render(){
 let list=page==='saved'?songs.filter(s=>saved.includes(s.id)):songs.filter(s=>s.id!==seed.id);
 const lang=$('#language').value;if(lang!=='all')list=list.filter(s=>s.language===lang);
 if(alternate&&page!=='saved')list=[...list].reverse();
 $('#song-grid').innerHTML=list.map((s,i)=>`<article class="song-card"><div class="cover-wrap"><img src="assets/covers/${s.cover}.svg" alt="Ilustración de muestra para ${s.title}; portada no oficial"><span class="cover-corner">SONORA / 0${i+1}</span><span class="cover-label">${s.title}<small>RUTAS POR DESCUBRIR</small></span></div><button class="song-link" data-detail="${s.id}">${s.title}</button><p class="song-artist">${s.artist}</p><button class="save-song" data-save="${s.id}" aria-label="${saved.includes(s.id)?'Quitar de':'Añadir a'} guardadas: ${s.title}" aria-pressed="${saved.includes(s.id)}"><svg><use href="#i-heart"/></svg></button><p class="song-reason"><span>↳</span>${reason(s)}</p><div class="song-language">${s.language==='es'?'ESPAÑOL':'INGLÉS'} · ${mode==='mixed'?'LETRAS + MÚSICA':mode==='lyrics'?'LETRAS':'MÚSICA'}</div></article>`).join('');
 $('#empty-state').hidden=list.length>0;$('#song-grid').hidden=list.length===0;
 if(page==='saved'){
  $('#section-eyebrow').textContent='TU COLECCIÓN';$('#recommendation-title').textContent='Canciones guardadas';$('#recommendation-subtitle').textContent='Hallazgos que merecen otra vuelta.';
  $('#empty-title').textContent=saved.length?'No hay guardadas en este idioma':'Tu mapa empieza aquí';$('#empty-copy').textContent=saved.length?'Prueba otro idioma para ver tus canciones guardadas.':'Guarda una canción con el corazón para volver a encontrarla.';
 }else{
  $('#section-eyebrow').textContent='EL SIGUIENTE TRAMO';const h=$('#recommendation-title');h.textContent='Si te mueve ';const span=document.createElement('span');span.textContent=seed.title;h.append(span);
  $('#recommendation-subtitle').textContent=`${seed.artist} como punto de partida. El resto, por descubrir.`;
  $('#empty-title').textContent='Esta ruta aún no tiene canciones';$('#empty-copy').textContent='Prueba otro idioma para ampliar el horizonte.';
 }
 $('#refresh-route').hidden=page==='saved';$('#saved-count').textContent=saved.length;
 $$('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
}
function changeMode(next){mode=next;$$('[data-mode]').forEach(b=>{b.classList.toggle('selected',b.dataset.mode===mode);b.setAttribute('aria-pressed',String(b.dataset.mode===mode));});$('#mix-block').hidden=mode!=='mixed';$('#mode-explanation').textContent={lyrics:'Historias, temas y emociones que conectan con tu canción.',music:'Ritmo, energía e instrumentación para seguir la misma vibra.',mixed:'Un poco de lo que dice. Un poco de cómo suena.'}[mode];render();}
function updateMix(){const val=+$('#mix-range').value;$('#lyrics-percent').textContent=(100-val)+'%';$('#music-percent').textContent=val+'%';$('#mix-range').style.background=`linear-gradient(to right,var(--accent) ${val}%,var(--line) ${val}%)`;$('#mix-range').setAttribute('aria-valuetext',`${100-val}% letras, ${val}% música`);render();}
function toggleSave(id){const song=songs.find(s=>s.id===id);saved=saved.includes(id)?saved.filter(s=>s!==id):[...saved,id];try{localStorage.setItem('sonora-visual-saved',JSON.stringify(saved));}catch{storageAvailable=false;}render();notify(saved.includes(id)?`${song.title} guardada${storageAvailable?'':' durante esta visita'}`:`${song.title} retirada de guardadas`);}
function showResults(){const q=$('#song-search').value.trim();if(!q){$('#search-results').hidden=true;$('#song-search').setAttribute('aria-expanded','false');return;}
 const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();const tokens=normalize(q).split(/\s+/).filter(Boolean);const matches=songs.filter(s=>tokens.every(t=>normalize(s.title+' '+s.artist).includes(t)));
 $('#search-results').innerHTML=matches.length?matches.map(s=>`<button type="button" data-seed="${s.id}"><img src="assets/covers/${s.cover}.svg" alt=""><span><b>${s.title}</b><small>${s.artist}</small></span><svg><use href="#i-arrow"/></svg></button>`).join(''):'<p>No encontramos esa canción en la muestra. Prueba «Hasta la Raíz», «Brillas», «Eres», «San Lucas» o «Bloom».</p>';
 $('#search-results').hidden=false;$('#song-search').setAttribute('aria-expanded','true');
}
function selectSeed(id){seed=songs.find(s=>s.id===id);page='discover';$('#song-search').value='';$('#search-results').hidden=true;$('#song-search').setAttribute('aria-expanded','false');alternate=false;render();notify(`Tu ruta parte de ${seed.title}`);}
function showDetail(id){const s=songs.find(s=>s.id===id);$('#dialog-content').innerHTML=`<img class="dialog-cover" src="assets/covers/${s.cover}.svg" alt="Ilustración de muestra, portada no oficial"><div class="dialog-kicker">UN NUEVO CAMINO · ${s.language==='es'?'ESPAÑOL':'INGLÉS'}</div><h2 class="dialog-title">${s.title}</h2><p class="dialog-artist">${s.artist}</p><p class="dialog-reason"><b>Por qué aparece en esta ruta</b>${reason(s)}</p><p class="dialog-note">Explicación editorial de ejemplo. La recomendación real se conectará en una siguiente etapa.</p><button class="primary-button" data-dialog-seed="${s.id}">Partir de esta canción <svg><use href="#i-arrow"/></svg></button>`;$('#song-dialog').showModal();}
$$('[data-direction]').forEach(b=>b.addEventListener('click',()=>setTheme(b.dataset.direction)));
$('.brief-toggle').addEventListener('click',()=>{const panel=$('#design-brief');panel.hidden=!panel.hidden;$('.brief-toggle').setAttribute('aria-expanded',String(!panel.hidden));$('.brief-toggle').innerHTML=(panel.hidden?'Ver concepto':'Cerrar concepto')+' <span>↗</span>';});
$$('[data-mode]').forEach(b=>b.addEventListener('click',()=>changeMode(b.dataset.mode)));
$('#mix-range').addEventListener('input',updateMix);
$('#filter-toggle').addEventListener('click',()=>{const f=$('#filters');f.hidden=!f.hidden;$('#filter-toggle').setAttribute('aria-expanded',String(!f.hidden));});
$('#language').addEventListener('change',render);
$('#exploration').addEventListener('input',()=>{const v=+$('#exploration').value;$('#explore-value').textContent=v<35?'Familiar':v>65?'Aventurero':'Equilibrado';$('#exploration').style.background=`linear-gradient(to right,var(--accent) ${v}%,var(--line) ${v}%)`;alternate=v>65;render();});
for(const id of ['limit-artists','exclude-covers']) $('#'+id).addEventListener('change',()=>{const n=$$('#filters input[type=checkbox]').filter(x=>x.checked).length;$('#filter-count').textContent=n;notify(id==='exclude-covers'?($('#exclude-covers').checked?'Covers excluidos. La muestra contiene composiciones distintas.':'Covers permitidos. Esta muestra no incluye versiones.'):($('#limit-artists').checked?'Máximo una canción por artista.':'Repetición de artistas permitida. La muestra contiene artistas distintos.'));});
$('#song-search').addEventListener('input',showResults);
$('#song-search').addEventListener('keydown',e=>{if(e.key==='Escape'){$('#search-results').hidden=true;$('#song-search').setAttribute('aria-expanded','false');}if(e.key==='ArrowDown'){const first=$('#search-results button');if(first){e.preventDefault();first.focus();}}});
$('#search-form').addEventListener('submit',e=>{e.preventDefault();if(!$('#song-search').value.trim()){$('#song-search').value='Hasta la Raíz';}showResults();});
$('#search-results').addEventListener('click',e=>{const b=e.target.closest('[data-seed]');if(b)selectSeed(b.dataset.seed);});
document.addEventListener('click',e=>{if(!$('#search-form').contains(e.target)){$('#search-results').hidden=true;$('#song-search').setAttribute('aria-expanded','false');}});
$('#song-grid').addEventListener('click',e=>{const save=e.target.closest('[data-save]');if(save){toggleSave(save.dataset.save);return;}const detail=e.target.closest('[data-detail]');if(detail)showDetail(detail.dataset.detail);});
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.page==='search'){$('#song-search').focus();$('#song-search').scrollIntoView({block:'center',behavior:'smooth'});return;}page=b.dataset.page;render();if(page==='saved')$('.recommendations').scrollIntoView({block:'start',behavior:'smooth'});}));
$$('[data-query]').forEach(b=>b.addEventListener('click',()=>selectSeed(songs.find(s=>s.title===b.dataset.query).id)));
$('#refresh-route').addEventListener('click',()=>{alternate=!alternate;render();notify('Otra ruta: mismos hallazgos, nuevo orden.');});
$('#back-discover').addEventListener('click',()=>{page='discover';$('#language').value='all';render();});
$('.dialog-close').addEventListener('click',()=>$('#song-dialog').close());
$('#song-dialog').addEventListener('click',e=>{if(e.target===$('#song-dialog'))$('#song-dialog').close();const b=e.target.closest('[data-dialog-seed]');if(b){$('#song-dialog').close();selectSeed(b.dataset.dialogSeed);}});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)&&!$('#song-dialog').open){e.preventDefault();$('#song-search').focus();}});
setTheme(themeFromUrl());updateMix();
