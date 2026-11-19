"""Compare 30 FMA clips by acoustic descriptors and build a local listening report."""
import csv
from html import escape
from itertools import combinations
import json
import os
from pathlib import Path
import random
import subprocess
import time
from urllib.parse import quote

import numpy as np
from scipy.fft import dct
from scipy.signal import correlate, stft


ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "data/processed/demo/lyrics_full_v1/demo_links.csv"
OUTPUT = ROOT / "runtime/audio-pilot"
RATE = 22050
FRAME = 2048
HOP = 512
SEED = 42
FAMILIES = ("Ritmo", "Energía", "Timbre", "Armonía")


def choose_tracks():
    with LINKS.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    rng = random.Random(SEED)
    rng.shuffle(rows)
    grouped = {}
    for row in rows:
        if row["split"] in ("train", "validation") and row["has_audio_file"] == "True":
            grouped.setdefault((row["split"], row["genre_top"]), []).append(row)
    return grouped


def decode(path):
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path),
         "-vn", "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
        capture_output=True, check=True, timeout=30,
    )
    audio = np.frombuffer(result.stdout, dtype="<f4")
    if audio.size < RATE * 5 or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-4:
        raise ValueError("clip demasiado corto, inválido o silencioso")
    return audio


def describe(audio):
    freq, _, spectrum = stft(audio, fs=RATE, nperseg=FRAME, noverlap=FRAME-HOP,
                             boundary=None, padded=False)
    power = np.abs(spectrum).astype(np.float64) ** 2
    total = np.maximum(power.sum(axis=0), 1e-12)
    loudness = 10 * np.log10(total)
    active = loudness > max(-65, float(loudness.max()) - 45)
    if active.sum() < 5:
        raise ValueError("clip sin suficientes ventanas activas")
    shape = np.sqrt(power / total)
    flux = np.maximum(np.diff(shape, axis=1), 0).sum(axis=0)
    centered = flux - flux.mean()
    ac = correlate(centered, centered, mode="full")[len(centered)-1:]
    frame_rate = RATE / HOP
    lags = np.arange(round(frame_rate*60/180), round(frame_rate*60/60) + 1)
    best = lags[np.argmax(ac[lags])]
    periodicity = max(0.0, float(ac[best] / max(ac[0], 1e-12)))
    bpm = float(frame_rate * 60 / best) if periodicity >= 0.15 else None

    mel = 2595 * np.log10(1 + freq / 700)
    edges = np.linspace(mel[1], mel[-1], 42)
    rising = (mel - edges[:-2, None]) / (edges[1:-1] - edges[:-2])[:, None]
    falling = (edges[2:, None] - mel) / (edges[2:] - edges[1:-1])[:, None]
    filters = np.maximum(0, np.minimum(rising, falling))
    mfcc = dct(np.log(np.maximum(filters @ power[:, active], 1e-12)),
               axis=0, norm="ortho")[1:13]
    centroid = (freq @ power[:, active]) / total[active]
    tonal = (freq >= 55) & (freq <= 4000)
    pitch = np.rint(69 + 12 * np.log2(freq[tonal] / 440)).astype(int) % 12
    chroma = np.bincount(pitch, weights=power[tonal][:, active].sum(axis=1), minlength=12)
    chroma /= max(chroma.sum(), 1e-12)
    bands = (filters @ power[:, active])
    proportions = bands / np.maximum(bands.sum(axis=0), 1e-12)
    occupied = (proportions >= 0.02).sum(axis=0)
    entropy = -np.sum(proportions * np.log(np.maximum(proportions, 1e-12)), axis=0)
    active_flux = flux[active[1:] & active[:-1]]
    if not active_flux.size:
        active_flux = flux
    attack_threshold = np.median(flux) + 2 * np.std(flux)
    attacks = (flux[1:-1] > attack_threshold) & (flux[1:-1] > flux[:-2]) & (flux[1:-1] >= flux[2:])
    persistence = np.sum(shape[:, 1:] * shape[:, :-1], axis=0)[active[1:] & active[:-1]]
    if not persistence.size:
        persistence = np.array([0.0])
    return {
        "seconds": float(audio.size / RATE), "bpm": bpm, "periodicity": periodicity,
        "blocks": [
            [float(flux.mean()), float(flux.std()), periodicity],
            [float(np.median(loudness[active])), float(np.std(loudness[active]))],
            [float(np.log1p(np.median(centroid))), *mfcc.mean(axis=1), *mfcc.std(axis=1)],
            chroma.tolist(),
        ],
        "arrangement": [float(np.median(occupied)), float(np.mean(entropy)),
                        float(np.median(active_flux)), float(np.quantile(active_flux, 0.9))],
        "texture_pulse": [float(np.mean(persistence)), float(np.std(persistence)),
                          float(attacks.sum() * RATE / audio.size), periodicity],
    }


def extract_sample():
    grouped = choose_tracks()
    sample, errors = [], []
    used_groups = set()
    for split in ("train", "validation"):
        count = 0
        buckets = [rows for (part, _), rows in sorted(grouped.items()) if part == split]
        while count < 15 and any(buckets):
            for bucket in buckets:
                while bucket and count < 15:
                    row = bucket.pop()
                    if row["group_id"] in used_groups:
                        continue
                    try:
                        features = describe(decode(ROOT / row["audio_path"]))
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as error:
                        errors.append({"id": row["fma_track_id"], "error": str(error)})
                        continue
                    sample.append(row | features)
                    used_groups.add(row["group_id"])
                    count += 1
                    break
        if count != 15:
            raise RuntimeError(f"Solo {count} clips válidos para {split}")
    return sample, errors


def rank(sample):
    training = np.array([row["split"] == "train" for row in sample])
    normalized = []
    for index in range(len(FAMILIES)):
        matrix = np.array([row["blocks"][index] for row in sample])
        scale = matrix[training].std(axis=0)
        scale[scale < 1e-8] = 1
        normalized.append((matrix - matrix[training].mean(axis=0)) / scale)
    pairs = []
    for first, second in combinations(range(len(sample)), 2):
        distances = [float(np.mean((block[first] - block[second]) ** 2))
                     for block in normalized]
        bpm_a, bpm_b = sample[first]["bpm"], sample[second]["bpm"]
        if bpm_a is not None and bpm_b is not None:
            tempo_gap = abs(np.log2(bpm_a / bpm_b))
            tempo_gap = min(tempo_gap, abs(tempo_gap - 1))
            distances[0] = (3 * distances[0] + (tempo_gap / 0.25) ** 2) / 4
        pairs.append({"indices": [first, second], "distance": float(np.sqrt(np.mean(distances))),
                      "family_distances": dict(zip(FAMILIES, np.sqrt(distances).tolist()))})
    return sorted(pairs, key=lambda pair: pair["distance"])


def audio_card(row, details=True):
    title = escape(row["fma_title"])
    artist = escape(row["fma_artist"])
    relative = os.path.relpath(ROOT / row["audio_path"], OUTPUT).replace(os.sep, "/")
    tempo = f'{row["bpm"]:.0f} BPM' if row["bpm"] is not None else "tempo incierto"
    metadata = (f' · {escape(row["genre_top"])}<br>{row["seconds"]:.1f} s · {tempo}'
                f' · FMA {row["fma_track_id"]}') if details else ''
    return (f'<div><strong>{title}</strong><br>{artist}{metadata}'
            f'<br><audio controls preload="none" src="{quote(relative)}"></audio></div>')


def listening_report(sample, pairs):
    ranked = [*enumerate(pairs[:8], 1), (len(pairs)//2 + 1, pairs[len(pairs)//2]),
              (len(pairs), pairs[-1])]
    cards = []
    for position, pair in ranked:
        first, second = (sample[index] for index in pair["indices"])
        label = f"Par {position}" if position <= 8 else ("Control intermedio" if position < len(pairs) else "Control distante")
        key = f'audio-pilot-42-{position}-{first["fma_track_id"]}-{second["fma_track_id"]}'
        cards.append(
            f'<section><h2>{label} <small>Distancia {pair["distance"]:.2f}</small></h2>'
            f'<div class="pair">{audio_card(first)}{audio_card(second)}</div>'
            f'<label>¿Se parecen al escucharlas? <select data-key="{key}"><option value="">Sin evaluar</option>'
            '<option>Mucho</option><option>Algo</option><option>Poco</option><option>Nada</option></select></label></section>'
        )
    return """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SONORA · Prueba de audio</title><style>
body{margin:2rem auto;padding:0 1rem;max-width:850px;font:17px system-ui;background:#f8f5ee;color:#241c17}
section{border:1px solid #d6cabe;border-radius:12px;background:white;padding:1rem;margin:1rem 0}
h2{font-size:1.15rem;margin-top:0}small{font-weight:400;color:#62564e;margin-left:.5rem}
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}
audio{width:100%;margin:.6rem 0}select{font:inherit}
</style><h1>SONORA · Prueba de audio</h1>
<p>30 clips de FMA Medium y 435 pares. Una distancia menor indica mayor semejanza según los descriptores. Escucha ambos clips y registra tu impresión. Las valoraciones se guardan en este navegador si permite almacenamiento local.</p>
""" + "".join(cards) + """<details><summary>Escuchar los 30 clips</summary><div class="pair">""" + "".join(
        audio_card(row) for row in sample
    ) + """</div></details><script>
for (const rating of document.querySelectorAll("select[data-key]")) {
  try {
    rating.value = localStorage.getItem(rating.dataset.key) || "";
    rating.addEventListener("change", () => localStorage.setItem(rating.dataset.key, rating.value));
  } catch {}
}
document.addEventListener("play", event => {
  if (event.target.tagName === "AUDIO") {
    for (const audio of document.querySelectorAll("audio")) if (audio !== event.target) audio.pause();
  }
}, true);
</script></html>"""


def followup_report(sample, pairs):
    ids = {row["fma_track_id"]: index for index, row in enumerate(sample)}
    known = [(129476, 72050), (148168, 129476), (66202, 21083), (14957, 118650)]
    choices = [tuple(sorted(ids[str(track)] for track in pair)) for pair in known]
    excluded = set(choices) | {tuple(pair["indices"]) for pair in pairs[:8]}
    excluded.update(tuple(pair["indices"]) for pair in (pairs[len(pairs)//2], pairs[-1]))
    train = [row["split"] == "train" for row in sample]
    def compare(key):
        values = np.array([row[key] for row in sample])
        scales = values[train].std(axis=0)
        scales[scales < 1e-8] = 1
        normalized = values / scales
        return sorted(combinations(range(len(sample)), 2),
                      key=lambda pair: np.linalg.norm(normalized[pair[0]] - normalized[pair[1]]))

    used_new = set()
    for key in ("arrangement", "texture_pulse"):
        for pair in compare(key):
            if pair not in excluded and used_new.isdisjoint(pair):
                choices.append(pair)
                excluded.add(pair)
                used_new.update(pair)
                if len(choices) in (6, 8):
                    break
    assert len(choices) == 8
    random.Random(SEED + 1).shuffle(choices)
    cards = []
    for number, (a, b) in enumerate(choices, 1):
        controls = []
        for axis, label in (("arreglo", "Arreglo"), ("textura", "Textura y pulso")):
            key = f"ronda-2-{sample[a]['fma_track_id']}-{sample[b]['fma_track_id']}-{axis}"
            controls.append(f'<label>{label} <select data-key="{key}"><option value="">Sin evaluar</option>'
                            '<option>Mucho</option><option>Algo</option><option>Poco</option>'
                            '<option>Nada</option></select></label>')
        cards.append(f'<section><h2>Par {number}</h2><div class="pair">'
                     f'{audio_card(sample[a], details=False)}{audio_card(sample[b], details=False)}</div>'
                     f'<div class="pair">{"".join(controls)}</div></section>')
    return """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SONORA · Segunda escucha</title><style>
body{margin:2rem auto;padding:0 1rem;max-width:850px;font:17px system-ui;background:#f8f5ee;color:#241c17}
section{border:1px solid #d6cabe;border-radius:12px;background:white;padding:1rem;margin:1rem 0}
h2{font-size:1.15rem;margin-top:0}.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}
audio{width:100%;margin:.6rem 0}select,textarea{font:inherit}textarea{width:100%;box-sizing:border-box}
</style><h1>SONORA · Segunda escucha</h1>
<p>Escucha los dos clips de cada par y marca cuánto se parecen en cada dimensión.</p>
<ul><li><strong>Arreglo:</strong> qué tan cargados suenan y cuánto movimiento hay.</li>
<li><strong>Textura y pulso:</strong> cómo suenan y se sostienen las voces o instrumentos y qué ritmo percibes.</li></ul>
""" + "".join(cards) + """<label for="summary">Respuestas para compartir</label>
<textarea id="summary" readonly rows="9"></textarea>
<script>
const ratings = [...document.querySelectorAll('select[data-key]')];
function update() {
  document.querySelector('#summary').value = [...document.querySelectorAll('section')].map(section => {
    const [arrangement, texture] = section.querySelectorAll('select');
    return section.querySelector('h2').textContent + ': arreglo ' + (arrangement.value || '—')
      + ' | textura y pulso ' + (texture.value || '—');
  }).join('\\n');
}
for (const rating of ratings) {
  try { rating.value = localStorage.getItem(rating.dataset.key) || ''; } catch {}
  rating.addEventListener('change', () => {
    try { localStorage.setItem(rating.dataset.key, rating.value); } catch {}
    update();
  });
}
document.addEventListener('play', event => {
  if (event.target.tagName === 'AUDIO') {
    for (const clip of document.querySelectorAll('audio')) if (clip !== event.target) clip.pause();
  }
}, true);
update();
</script></html>"""


def main():
    started = time.perf_counter()
    sample, errors = extract_sample()
    pairs = rank(sample)
    assert len(sample) == 30 and len(pairs) == 435
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "resultados.json").write_text(json.dumps({
        "seed": SEED, "sample_rate": RATE, "stft_frame": FRAME, "stft_hop": HOP,
        "training_tracks": 15, "validation_tracks": 15,
        "tracks": sample, "pairs": pairs, "errors": errors,
        "elapsed_seconds": time.perf_counter() - started,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "escuchar.html").write_text(listening_report(sample, pairs), encoding="utf-8")
    (OUTPUT / "ronda-2.html").write_text(followup_report(sample, pairs), encoding="utf-8")
    print(f"{len(sample)} clips, {len(pairs)} pares, {len(errors)} errores")
    for pair in pairs[:8]:
        first, second = (sample[index] for index in pair["indices"])
        print(f'{pair["distance"]:.3f} | {first["fma_title"]} — {first["fma_artist"]}'
              f' / {second["fma_title"]} — {second["fma_artist"]}')


if __name__ == "__main__":
    main()
