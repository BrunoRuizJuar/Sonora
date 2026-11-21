const slides = [...document.querySelectorAll('.slide')];
const deck = document.querySelector('#slides');
const slideScroll = document.querySelector('.slide-scroll');
const pdf = document.querySelector('#pdf-frame');
const player = document.querySelector('#demo-frame');
const switchButton = document.querySelector('#presentation-switch');
const formatLink = document.querySelector('#presentation-format');
const openPdf = document.querySelector('#open-pdf');
const fullscreen = document.querySelector('#fullscreen');
const previous = document.querySelector('#previous-slide');
const next = document.querySelector('#next-slide');
const status = document.querySelector('#slide-status');
const progress = document.querySelector('#slide-progress');
const storageKey = pdf ? 'sonora:presentation-slide' : 'sonora:research-slide';
const showOutline = !pdf || new URLSearchParams(location.search).get('guion') === '1' ||
  slides.some(slide => '#' + slide.getAttribute('aria-labelledby') === location.hash);
const presentation = showOutline ? deck : pdf;
let current = 0;

function initialSlide() {
  const linked = slides.findIndex(slide => '#' + slide.getAttribute('aria-labelledby') === location.hash);
  if (linked >= 0) return linked;
  try {
    const saved = Number(sessionStorage.getItem(storageKey));
    return Number.isInteger(saved) && saved >= 0 && saved < slides.length ? saved : 0;
  } catch {
    return 0;
  }
}

function showSlide(index, focusHeading = false) {
  current = Math.max(0, Math.min(index, slides.length - 1));
  const active = slides[current];
  slides.forEach(slide => { slide.hidden = slide !== active; });
  previous.disabled = current === 0;
  next.disabled = current === slides.length - 1;
  status.textContent = `${current + 1} / ${slides.length}`;
  if (active.dataset.time) status.textContent += ` · ${active.dataset.time}`;
  progress.max = slides.length;
  progress.value = current + 1;
  const heading = document.getElementById(active.getAttribute('aria-labelledby'));
  history.replaceState(null, '', '#' + heading.id);
  try {
    sessionStorage.setItem(storageKey, current);
  } catch {
    // The URL still retains the slide when storage is unavailable.
  }
  slideScroll.scrollTop = 0;
  if (focusHeading) heading.focus({ preventScroll: true });
}

function showPlayer(open) {
  if (open && !player.hasAttribute('src')) player.src = showOutline ? '/#song-search' : '/reproductor.html?presentacion=1';
  player.hidden = !open;
  presentation.classList.toggle('behind-demo', open);
  presentation.inert = open;
  switchButton.textContent = open ? 'Volver a la presentación' : 'Demo en vivo';
  switchButton.setAttribute('aria-expanded', String(open));
  switchButton.focus();
}

switchButton?.addEventListener('click', () => showPlayer(player.hidden));
document.querySelector('#demo-player')?.addEventListener('click', () => showPlayer(true));
previous.addEventListener('click', () => showSlide(current - 1, true));
next.addEventListener('click', () => showSlide(current + 1, true));

document.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  if (!showOutline || (player && !player.hidden)) return;
  const destination = {
    ArrowLeft: current - 1,
    PageUp: current - 1,
    ArrowRight: current + 1,
    PageDown: current + 1,
    Home: 0,
    End: slides.length - 1,
  }[event.key];
  if (destination === undefined) return;
  event.preventDefault();
  showSlide(destination, true);
});

if (document.fullscreenEnabled) {
  fullscreen.hidden = false;
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      fullscreen.textContent = 'Pantalla completa no disponible';
    }
  });
  document.addEventListener('fullscreenchange', () => {
    fullscreen.textContent = document.fullscreenElement ? 'Salir de pantalla completa' : 'Pantalla completa';
  });
}

if (showOutline) {
  if (pdf) {
    pdf.hidden = true;
    formatLink.href = '/presentacion.html';
    formatLink.textContent = 'Ver PDF original';
    openPdf.hidden = true;
  }
  deck.hidden = false;
  window.addEventListener('hashchange', () => showSlide(initialSlide()));
  showSlide(initialSlide());
}
if (switchButton) switchButton.hidden = false;
