"""Construye y ejecuta la Evidencia 2 (estadística y modelos del lenguaje).

  .venv\\Scripts\\python.exe notebooks\\evidencias\\build_e2.py

Requiere las salidas de pipelines/nlp/count_ngrams.py, pipelines/nlp/e2_frequency.py y
pipelines/nlp/ngram_lm.py (ver la tabla de la primera celda).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbbuild import ROOT, build, code, md  # noqa: E402

CELLS = [
md(r"""
# Evidencia 2 — Estadística del corpus y modelo de lenguaje de n-gramas

**Proyecto:** SONORA · **Materia:** Procesamiento de Lenguaje Natural · **Requisitos:** E2-01 … E2-05 (`docs/REQUIREMENTS.md` v1.2)

**Universo:** el corpus **completo** `lyrics_full_v1` (3 155 772 letras canónicas en inglés).
Las métricas descriptivas (secciones 1–6) usan **todas** las letras; el modelo de lenguaje
(sección 7) **aprende sólo con `train`** y se evalúa en `validation`; `test` no se usa aquí
(queda reservado para la evaluación final). Cuando una celda muestra ejemplos de una muestra lo
declara.

**Unidad de conteo («token» en E2).** Palabra regex `regex-words-v1`: secuencias máximas de
letras Unicode con apóstrofos internos (`don't`, `y'all` = 1 token), en minúsculas, sobre la vista
de análisis (sin anotaciones editoriales entre corchetes). Números y puntuación no son palabras.
No es la tokenización de spaCy (que separa `do` + `n't`); spaCy se usa sólo para el POS que define
los vocablos (sección 3).

**Frontera de n-gramas:** el verso. Ningún bigrama/trigrama cruza un salto de línea; los
marcadores `<s>`/`</s>` existen sólo en los conteos de `train` para el modelo de lenguaje y se
excluyen de todas las tablas descriptivas.

| Etapa | Comando | Salida |
|---|---|---|
| Conteo de n-gramas 1–3 por split | `pipelines/nlp/count_ngrams.py` | `data/processed/nlp/lyrics_full_v1/ngrams/counts` |
| Léxico POS (spaCy) por split | `pipelines/nlp/e2_frequency.py pos-lexicon` | `frequency/word_pos.parquet`, `group_pos.parquet` |
| Candidatos a vocablo (sólo train) | `pipelines/nlp/e2_frequency.py vocable-candidates` | `frequency/vocable_candidates.json` → revisión → `config/vocables.yaml` |
| Unigramas por tag y década | `pipelines/nlp/e2_frequency.py group-unigrams` | `frequency/group_unigrams/group_unigrams.parquet` |
| Resumen de n-gramas (totales, espectro, top-K) | `pipelines/nlp/e2_frequency.py ngram-summary` | `frequency/ngram_summary.json` |
| Vocabulario y texto del modelo | `pipelines/nlp/e2_frequency.py lm-vocab` / `lm-export` | `lm/vocab_train_min2.txt`, `lm/text/shards/` |
| KenLM (WSL) | `scripts/kenlm/build_kenlm.sh`; `pipelines/nlp/ngram_lm.py train/eval` | `lm/results.json` |
"""),
code(r"""
import json, math, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pyarrow as pa, pyarrow.compute as pc, pyarrow.dataset as ds, pyarrow.parquet as pq
import matplotlib.pyplot as plt
import yaml

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))
from sonora import viz
viz.apply_style()

RUN = "lyrics_full_v1"
NLP = ROOT / "data/processed/nlp" / RUN
FIG = ROOT / "reports/figures/E2"
S = json.loads((NLP / "frequency/ngram_summary.json").read_text(encoding="utf-8"))
O = S["orders"]
manifest = json.loads((ROOT / "manifests/nlp" / f"{RUN}.json").read_text(encoding="utf-8"))
lex = pq.read_table(NLP / "lexicon/lexicon.parquet")
VOC = yaml.safe_load((ROOT / "config/vocables.yaml").read_text(encoding="utf-8"))
VOCABLES = set(VOC["vocables"])
from spacy.lang.en.stop_words import STOP_WORDS
STOP = {w.lower() for w in STOP_WORDS}

def fmt(n): return f"{n:,}".replace(",", " ")
def show(rows, cols=None):
    from IPython.display import Markdown, display
    cols = cols or list(rows[0])
    def cell(v):
        if isinstance(v, float): return f"{v:,.3f}".replace(",", " ")
        if isinstance(v, (int, np.integer)): return fmt(int(v))
        return str(v)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(r[c]) for c in cols) + " |" for r in rows]
    display(Markdown("\n".join(lines)))
print("Resumen de n-gramas:", S["version"], "|", S["partitions"], "particiones |", S["note"])
print("Stopwords spaCy:", len(STOP), "| vocablos:", len(VOCABLES), f"({VOC['version']})")
"""),
md(r"""
## 1. Universo de tokens y reconciliación (E2-01)

Antes de interpretar, los totales del resumen de n-gramas deben coincidir con el léxico
construido de forma independiente (`annotate_corpus.py lexicon`) y con el manifiesto del conteo.
"""),
code(r"""
lex_tokens = int(pc.sum(lex["count"]).as_py())
ng_summary = json.loads((NLP / "ngrams/summary.json").read_text(encoding="utf-8"))
rows = []
for scope in ("all", "train", "validation", "test"):
    u = O["1"][scope]
    ref = lex_tokens if scope == "all" else ng_summary["totals_by_split"][scope]["tokens"]
    rows.append({"alcance": scope, "tokens (unigramas)": u["tokens"], "tipos": u["types"],
                 "referencia": ref, "coincide": "sí" if u["tokens"] == ref else "NO"})
show(rows)
assert all(r["coincide"] == "sí" for r in rows)
assert O["1"]["all"]["types"] == lex.num_rows
N = O["1"]["all"]["tokens"]
print(f"Universo: {fmt(N)} tokens, {fmt(O['1']['all']['types'])} tipos, {fmt(lex.num_rows)} filas del léxico.")
"""),
md(r"""
## 2. Frecuencias absolutas y relativas con y sin palabras funcionales (E2-01)

Tres políticas sobre el **mismo** universo de tokens: (a) todas las palabras; (b) sin las 326
*stopwords* de spaCy 3.8 (palabras funcionales y algunos adverbios frecuentes); (c) sin
stopwords ni vocablos/muletillas (sección 3). La frecuencia relativa se expresa por millón de
tokens del universo completo, de modo que las tres columnas son comparables.

La comparación se justifica porque (a) mide la distribución real (base de Zipf y del modelo de
lenguaje), mientras (b) y (c) revelan el contenido temático que las palabras funcionales y los
vocablos ocultan en el top.
"""),
code(r"""
words = lex["word"].to_pylist(); counts = lex["count"].to_numpy(); dfreq = lex["doc_freq"].to_numpy()
is_stop = np.array([w in STOP for w in words]); is_voc = np.array([w in VOCABLES for w in words])
D = 3155772
def top(mask, k=25):
    idx = np.flatnonzero(mask)[:k]  # el léxico ya está ordenado por frecuencia descendente
    cum = 0; out = []
    for r, i in enumerate(idx, 1):
        cum += counts[i]
        out.append({"rango": r, "palabra": words[i], "frecuencia": int(counts[i]),
                    "por millón": 1e6 * counts[i] / N, "% acumulado": 100 * cum / N,
                    "% de letras": 100 * dfreq[i] / D})
    return out
pol = {"a) todas": np.ones(len(words), bool), "b) sin stopwords": ~is_stop, "c) sin stopwords ni vocablos": ~is_stop & ~is_voc}
for name, m in pol.items():
    print(name); show(top(m, 20))
show([{"política": n, "tokens que quedan": int(counts[m].sum()), "% del universo": 100 * counts[m].sum() / N,
       "tipos": int(m.sum())} for n, m in pol.items()])
"""),
code(r"""
fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharex=False)
for ax, (name, m) in zip(axes, pol.items()):
    t = top(m, 15)[::-1]
    ax.barh([r["palabra"] for r in t], [r["por millón"] for r in t], color=viz.SEQUENTIAL, height=0.7)
    ax.set_title(name, fontsize=11); ax.set_xlabel("por millón de tokens")
    ax.grid(axis="y", visible=False)
fig.suptitle("Las 15 palabras más frecuentes según la política de filtrado", x=0.01, ha="left", fontweight="bold")
viz.caption(axes[0], f"Universo: {fmt(N)} tokens regex del corpus completo (3 155 772 letras). Mismo denominador en los tres paneles.")
fig.tight_layout(); viz.save(fig, FIG / "e2_top_palabras_politicas.png"); plt.show()
"""),
md(r"""
## 3. Vocablos y muletillas: lista derivada de los datos (E2-01)

Un *vocablo* es una palabra no léxica de relleno o expresión (`oh`, `yeah`, `na`, `ooh`). La
lista no se escribió a mano: se derivó **sólo de `train`** con dos criterios y luego se revisó.

1. **POS mayoritario `INTJ`** en la anotación spaCy de `train` (forma en minúsculas, ≥ 100
   apariciones);
2. **patrón de sílabas**: una sílaba corta repetida (`nana`, `lalala`) o una letra alargada
   tres o más veces (`ooooh`), con ≥ 100 apariciones.

La revisión excluye interjecciones con contenido léxico (saludos, cortesía, insultos, `yes`/`no`)
y registra cada exclusión con su motivo en `config/vocables.yaml`.
"""),
code(r"""
cand = json.loads((NLP / "frequency/vocable_candidates.json").read_text(encoding="utf-8"))
reasons = Counter(r for c in cand for r in c["reasons"])
print(f"Candidatos (train, ≥100): {len(cand)} | por criterio: {dict(reasons)}")
print(f"Lista final: {len(VOCABLES)} vocablos | excluidos en revisión: {len(VOC['excluded'])}")
show([{"forma": c["form"], "frecuencia train": c["count"], "POS mayoritario": c["majority_upos"],
       "% INTJ": 100 * c["intj_share"], "criterio": ", ".join(c["reasons"]),
       "decisión": "vocablo" if c["form"] in VOCABLES else "excluido: " + VOC["excluded"].get(c["form"], "?")}
      for c in cand[:40]])
voc_tokens = int(counts[is_voc].sum())
print(f"Los vocablos suman {fmt(voc_tokens)} tokens ({100*voc_tokens/N:.2f} % del universo completo).")
"""),
code(r"""
# Peso de los vocablos por tag (corpus completo; tokens regex; denominador = tokens del tag).
gu = pq.read_table(NLP / "frequency/group_unigrams/group_unigrams.parquet")
tg = gu.filter(pc.equal(gu["kind"], "tag"))
by = {}
for g, w, c in zip(tg["group"].to_pylist(), tg["word"].to_pylist(), tg["count"].to_pylist()):
    b = by.setdefault(g, [0, 0, 0]); b[0] += c
    if w in VOCABLES: b[1] += c
    if w in STOP: b[2] += c
show([{"tag": t, "tokens": by[t][0], "vocablos por 1000": 1000 * by[t][1] / by[t][0],
       "stopwords %": 100 * by[t][2] / by[t][0]} for t in viz.TAG_ORDER])
assert sum(v[0] for v in by.values()) == N
"""),
md(r"""
## 4. n-gramas (E2-02)

Reglas: tokens regex en minúsculas; bigramas y trigramas **dentro del verso**; sin marcadores;
conteos sobre el corpus completo (suma de los tres splits). El filtro «contenido» elimina todo
n-grama que contenga al menos una stopword o un vocablo.
"""),
code(r"""
rows = []
for o in ("1", "2", "3"):
    a = O[o]["all"]; sp = a["spectrum_le1000"]
    rows.append({"orden": int(o), "ocurrencias": a["tokens"], "tipos": a["types"],
                 "hapax (f=1)": sp.get("1", 0), "% tipos hapax": 100 * sp.get("1", 0) / a["types"],
                 "tipos/ocurrencias": a["types"] / a["tokens"]})
show(rows)
def ngram_table(order, key, k=20):
    t = O[order]["all"][key][:k]
    tot = O[order]["all"]["tokens"]
    return [{"rango": i, "n-grama": g, "frecuencia": c, "por millón": 1e6 * c / tot} for i, (g, c) in enumerate(t, 1)]
for o, name in (("2", "Bigramas"), ("3", "Trigramas")):
    print(name, "— todos"); show(ngram_table(o, "top"))
    print(name, "— contenido (sin stopwords ni vocablos)"); show(ngram_table(o, "top_content"))
"""),
code(r"""
# Ejemplos de patrones: n-gramas formados sólo por vocablos (repetición de sílabas) frente a
# n-gramas con verbo de contenido; se buscan en los top-K guardados (K = 2000 por orden).
def only_vocables(g): return all(w in VOCABLES for w in g.split())
for o in ("2", "3"):
    t = O[o]["all"]["top"]
    v = [(g, c) for g, c in t if only_vocables(g)]
    share = sum(c for _, c in v) / sum(c for _, c in t)
    print(f"Orden {o}: {len(v)} de los {len(t)} n-gramas más frecuentes son sólo vocablos "
          f"({100*share:.1f} % de sus ocurrencias). Ejemplos: {', '.join(g for g, _ in v[:8])}")
pron = [(g, c) for g, c in O["3"]["all"]["top"] if g.split()[0] in {"i", "you"}][:12]
print("Trigramas que empiezan con 'i'/'you':", "; ".join(f"{g} ({fmt(c)})" for g, c in pron))
"""),
md(r"""
## 5. Rango–frecuencia: ley de Zipf y sus desviaciones (E2-03)

Se ajusta $\log f = \log C - \alpha \log r$ por mínimos cuadrados sobre rangos espaciados
logarítmicamente (para no dar peso desmedido a la cola) en un tramo central declarado, y un
modelo de Zipf–Mandelbrot $f = C/(r+b)^{\alpha}$ (búsqueda en rejilla de $b$, mínimos cuadrados
en $\alpha$, $C$). No se presupone que la ley se cumpla: se informan $R^2$ y los residuos por
tramo.
"""),
code(r"""
def rank_freq(order, scope="all"):
    a = O[order][scope]
    hi = np.array(a.get("counts_gt1000", []), dtype=float)
    spec = {int(k): v for k, v in a["spectrum_le1000"].items()}
    fvals = np.concatenate([np.sort(np.unique(hi))[::-1], np.array(sorted(spec, reverse=True), float)])
    mult = np.concatenate([[int((hi == f).sum()) for f in np.sort(np.unique(hi))[::-1]], [spec[int(f)] for f in sorted(spec, reverse=True)]])
    return fvals, np.cumsum(mult)  # frecuencia distinta (desc.) y rango final de cada escalón
def f_at(fvals, cum, ranks):
    return fvals[np.searchsorted(cum, ranks)]
def zipf_fit(order, r_lo, r_hi, n=200):
    fv, cum = rank_freq(order)
    r = np.unique(np.logspace(np.log10(r_lo), np.log10(r_hi), n).astype(int))
    x, y = np.log10(r), np.log10(f_at(fv, cum, r))
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef; r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    best = None
    for b in np.concatenate([[0], np.logspace(-1, 3, 200)]):
        xb = np.log10(r + b); Ab = np.vstack([np.ones_like(xb), xb]).T
        cb, *_ = np.linalg.lstsq(Ab, y, rcond=None); sse = ((y - Ab @ cb) ** 2).sum()
        if best is None or sse < best[0]: best = (sse, b, cb)
    return {"alpha": -coef[1], "logC": coef[0], "r2": r2, "zm_b": best[1], "zm_alpha": -best[2][1],
            "zm_r2": 1 - best[0] / ((y - y.mean()) ** 2).sum(), "ranks": r, "y": y, "pred": pred}
fits = {}
for o in ("1", "2", "3"):
    fv, cum = rank_freq(o)
    r_hi = int(cum[np.searchsorted(-fv, -10, side="right") - 1])  # último rango con f ≥ 10
    fits[o] = zipf_fit(o, 1, r_hi); fits[o]["r_hi"] = r_hi
    fits[o + "c"] = zipf_fit(o, 10, r_hi); fits[o + "c"]["r_hi"] = r_hi
show([{"orden": o, "tramo de rangos": f"1–{fmt(fits[o]['r_hi'])}", "α (Zipf, desde r=1)": fits[o]["alpha"], "R²": fits[o]["r2"],
       "α (desde r=10)": fits[o + "c"]["alpha"], "R² (r≥10)": fits[o + "c"]["r2"],
       "Zipf–Mandelbrot b": fits[o]["zm_b"], "α ZM": fits[o]["zm_alpha"], "R² ZM": fits[o]["zm_r2"]} for o in ("1", "2", "3")])
print("Tramo: rangos con frecuencia ≥ 10 (por encima, la meseta de frecuencias 1–9 es escalonada).")
"""),
code(r"""
fig, (ax, axr) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
names = {"1": "unigramas", "2": "bigramas", "3": "trigramas"}
for i, o in enumerate(("1", "2", "3")):
    fv, cum = rank_freq(o)
    ax.loglog(cum, fv, drawstyle="steps-post", color=viz.CATEGORICAL[i], label=f"{names[o]} ({fmt(int(cum[-1]))} tipos)")
f1 = fits["1"]
ax.loglog(10 ** np.log10(f1["ranks"]), 10 ** f1["pred"], color=viz.TEXT, linestyle="--", linewidth=1,
          label=f"ajuste Zipf unigramas α={f1['alpha']:.2f}")
ax.set_xlabel("rango (log)"); ax.set_ylabel("frecuencia (log)"); ax.set_title("Rango–frecuencia del corpus completo")
ax.legend(loc="lower left")
viz.caption(ax, "Universo: corpus completo, n-gramas dentro del verso sin marcadores. Escalones = tipos empatados.")
axr.semilogx(f1["ranks"], f1["y"] - f1["pred"], color=viz.CATEGORICAL[0])
axr.axhline(0, color=viz.MUTED, linewidth=0.8)
axr.set_xlabel("rango (log)"); axr.set_ylabel("residuo log10 (obs − ajuste)"); axr.set_title("Residuos del ajuste (unigramas)")
fig.tight_layout(); viz.save(fig, FIG / "e2_zipf.png"); plt.show()
r = f1["ranks"]; res = f1["y"] - f1["pred"]
show([{"tramo": lab, "residuo medio (log10)": float(res[m].mean()), "factor obs/ajuste": float(10 ** res[m].mean())}
      for lab, m in (("r ≤ 10", r <= 10), ("10 < r ≤ 1 000", (r > 10) & (r <= 1000)),
                     ("1 000 < r ≤ 100 000", (r > 1000) & (r <= 100000)), ("r > 100 000", r > 100000))])
"""),
md(r"""
### Espectro de frecuencias y hapax (E2-03/E2-04)

$V(m)$ = número de tipos que aparecen exactamente $m$ veces. Bajo Zipf con exponente $\alpha$
cerca de 1 se espera que los hapax sean aproximadamente la mitad del vocabulario.
"""),
code(r"""
rows = []
for o in ("1", "2", "3"):
    a = O[o]["all"]; sp = {int(k): v for k, v in a["spectrum_le1000"].items()}
    rows.append({"orden": int(o), **{f"V({m})": sp.get(m, 0) for m in (1, 2, 3, 4, 5)},
                 "V(1)/tipos %": 100 * sp.get(1, 0) / a["types"], "V(2)/V(1)": sp.get(2, 0) / sp.get(1, 1),
                 "hapax % de ocurrencias": 100 * sp.get(1, 0) / a["tokens"]})
show(rows)
fig, ax = plt.subplots(figsize=(8, 4))
for i, o in enumerate(("1", "2", "3")):
    sp = {int(k): v for k, v in O[o]["all"]["spectrum_le1000"].items()}
    m = np.array(sorted(sp)); ax.loglog(m[m <= 200], [sp[k] for k in m[m <= 200]], marker="o", markersize=2.5,
                                        linewidth=1.2, color=viz.CATEGORICAL[i], label=names[o])
ax.set_xlabel("frecuencia m (log)"); ax.set_ylabel("tipos con frecuencia m, V(m) (log)")
ax.set_title("Espectro de frecuencias"); ax.legend()
viz.caption(ax, "Universo: corpus completo. m ≤ 200.")
viz.save(fig, FIG / "e2_espectro.png"); plt.show()
"""),
md(r"""
## 6. Patrón adicional: repetición y diferencias léxicas entre tags (E2-04)

### 6.1 Concentración: palabras que se repiten dentro de la misma letra

La frecuencia total mezcla dos cosas: cuántas letras usan una palabra y cuántas veces la
repiten. El cociente *ocurrencias por letra que la contiene* = `count / doc_freq` (léxico
completo) separa ambas: los estribillos y vocablos se repiten muchas veces en pocas letras.
"""),
code(r"""
conc = counts / dfreq
m = counts >= 100_000
idx = np.flatnonzero(m)
order_c = idx[np.argsort(-conc[idx])]
show([{"palabra": words[i], "frecuencia": int(counts[i]), "% de letras": 100 * dfreq[i] / D,
       "ocurrencias por letra que la usa": float(conc[i]), "vocablo": "sí" if is_voc[i] else ""} for i in order_c[:20]])
med_v = np.median(conc[m & is_voc]); med_o = np.median(conc[m & ~is_voc & ~is_stop]); med_s = np.median(conc[m & is_stop])
print(f"Mediana de ocurrencias por letra (palabras con ≥ 100 000 ocurrencias): vocablos {med_v:.2f} "
      f"(n={int((m & is_voc).sum())}), stopwords {med_s:.2f} (n={int((m & is_stop).sum())}), "
      f"resto {med_o:.2f} (n={int((m & ~is_voc & ~is_stop).sum())})")
"""),
code(r"""
fig, ax = plt.subplots(figsize=(8, 4.4))
for lab, mm, col in (("stopwords", m & is_stop, viz.MUTED), ("contenido", m & ~is_stop & ~is_voc, viz.CATEGORICAL[0]),
                     ("vocablos", m & is_voc, viz.CATEGORICAL[1])):
    ax.scatter(100 * dfreq[mm] / D, conc[mm], s=10, color=col, alpha=0.75, label=f"{lab} (n={int(mm.sum())})", linewidths=0)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("% de letras que contienen la palabra (log)"); ax.set_ylabel("ocurrencias por letra que la usa (log)")
ax.set_title("Difusión frente a repetición dentro de la letra"); ax.legend()
for i in order_c[:6]:
    ax.annotate(words[i], (100 * dfreq[i] / D, conc[i]), xytext=(4, 2), textcoords="offset points", fontsize=8, color=viz.TEXT)
viz.caption(ax, "Universo: palabras con ≥ 100 000 ocurrencias en el corpus completo (léxico regex).")
viz.save(fig, FIG / "e2_difusion_repeticion.png"); plt.show()
"""),
md(r"""
### 6.2 Palabras características de cada tag

Log-odds con prior de Dirichlet informativo (Monroe, Colaresi y Quinn, 2008): cada tag frente al
resto de tags, con el corpus completo como prior ($\alpha_0$ = 10 000 pseudo-conteos). Se
muestran palabras de contenido (sin stopwords ni vocablos) con ≥ 1 000 ocurrencias; el valor *z*
ordena por evidencia y no por tamaño del efecto solo. El tag es la etiqueta de la fuente, no un
género verificado.
"""),
code(r"""
vocab = [w for w, c, s, v in zip(words, counts, is_stop, is_voc) if c >= 1000 and not s and not v]
vi = {w: i for i, w in enumerate(vocab)}
Y = {t: np.zeros(len(vocab)) for t in viz.TAG_ORDER}
for g, w, c in zip(tg["group"].to_pylist(), tg["word"].to_pylist(), tg["count"].to_pylist()):
    if w in vi and g in Y: Y[g][vi[w]] += c
bg = sum(Y.values()); a0 = 10_000; alpha = a0 * bg / bg.sum()
def logodds(t):
    yi = Y[t]; yj = bg - yi; ni, nj = by[t][0], N - by[t][0]
    d = np.log((yi + alpha) / (ni + a0 - yi - alpha)) - np.log((yj + alpha) / (nj + a0 - yj - alpha))
    return d / np.sqrt(1 / (yi + alpha) + 1 / (yj + alpha)), d
LO = {t: logodds(t) for t in viz.TAG_ORDER}
show([{"tag": t, "más características (z)": ", ".join(vocab[i] for i in np.argsort(-LO[t][0])[:12])} for t in viz.TAG_ORDER])
"""),
code(r"""
fig, axes = plt.subplots(1, 5, figsize=(14, 4.4))
for ax, t in zip(axes, viz.TAG_ORDER):
    z, d = LO[t]; idx = np.argsort(-z)[:10][::-1]
    ax.barh([vocab[i] for i in idx], z[idx], color=viz.TAG_COLORS[t], height=0.7)
    ax.set_title(t, color=viz.TEXT, fontsize=11); ax.grid(axis="y", visible=False); ax.set_xlabel("z log-odds")
fig.suptitle("Palabras de contenido más características de cada tag (frente al resto)", x=0.01, ha="left", fontweight="bold")
viz.caption(axes[0], "Universo: corpus completo; palabras con ≥ 1 000 ocurrencias, sin stopwords ni vocablos.")
fig.tight_layout(); viz.save(fig, FIG / "e2_logodds_tags.png"); plt.show()
"""),
md(r"""
## 7. Modelo de lenguaje de n-gramas con KenLM (E2-05)

| Elemento | Decisión |
|---|---|
| Implementación | KenLM `lmplz` (compilado en WSL Ubuntu 24.04; commit en `lm/results.json`) |
| Datos de ajuste | **sólo `train`**: un verso por línea, tokens regex en minúsculas |
| Fronteras | cada verso es una «oración»: `lmplz` añade `<s>` y `</s>`; no hay n-gramas entre versos |
| Vocabulario | tipos con frecuencia ≥ 2 en train; el resto (hapax de train y palabras nuevas) → clase `<oov>` en train y validation, así la perplejidad incluye todos los tokens y es comparable entre órdenes |
| Suavizado | Kneser-Ney modificado interpolado (por defecto en `lmplz`), sin poda |
| Selección | orden elegido por perplejidad en `validation`; `test` no se usa |
| Métrica | perplejidad por token incluyendo `</s>` (`query -v summary`) |

La perplejidad mide qué tan predecible es el texto para el modelo; **no** mide la calidad de una
recomendación (VAL-06).
"""),
code(r"""
res_path = NLP / "lm/results.json"
LM = json.loads(res_path.read_text(encoding="utf-8"))
fr = manifest["frequency"]
print("Vocabulario:", fr["lm-vocab"])
tot = fr["lm-export"]["totals"]
tr = tot["train"]; val = {k: v for k, v in tot.items() if k.startswith("validation.")}
vt = sum(v["tokens"] for v in val.values()); vo = sum(v["mapped_oov"] for v in val.values())
show([{"conjunto": "train", "letras": tr["docs"], "versos": tr["lines"], "tokens": tr["tokens"], "<oov>": tr["mapped_oov"],
       "% <oov>": 100 * tr["mapped_oov"] / tr["tokens"]},
      {"conjunto": "validation", "letras": sum(v["docs"] for v in val.values()), "versos": sum(v["lines"] for v in val.values()),
       "tokens": vt, "<oov>": vo, "% <oov>": 100 * vo / vt}])
rows = []
for key in sorted(LM, key=lambda k: int(k[1:])):
    e = LM[key]
    if "eval" not in e: continue
    rows.append({"orden": e["train"]["order"], **{f"{n}-gramas": e["train"]["ngram_counts"].get(f"{n}-gram", 0) for n in range(1, 5)},
                 "binario MB": e["train"]["files_bytes"].get(f"{key}.binary", 0) / 2**20,
                 "PPL validation": e["eval"]["validation"]["ppl_incl_oov"],
                 "OOV KenLM": e["eval"]["validation"]["kenlm_oovs"]})
show(rows)
best = min(rows, key=lambda r: r["PPL validation"]); BEST = f"o{best['orden']}"
print("Orden elegido por validation:", best["orden"])
"""),
code(r"""
ev = LM[BEST]["eval"]
show([{"tag": t, "tokens (incl. </s>)": ev[f"validation.{t}"]["tokens_incl_eos"],
       "PPL": ev[f"validation.{t}"]["ppl_incl_oov"]} for t in viz.TAG_ORDER])
fig, ax = plt.subplots(figsize=(8, 3.8))
for i, key in enumerate(sorted((k for k in LM if "eval" in LM[k]), key=lambda k: int(k[1:]))):
    vals = [LM[key]["eval"][f"validation.{t}"]["ppl_incl_oov"] for t in viz.TAG_ORDER]
    ax.plot(viz.TAG_ORDER, vals, marker="o", color=viz.CATEGORICAL[i], label=f"orden {key[1:]}")
ax.set_ylabel("perplejidad en validation"); ax.set_title("Perplejidad por tag y orden del modelo"); ax.legend()
viz.caption(ax, "Modelo aprendido sólo con train; evaluado en todas las letras de validation de cada tag.")
viz.save(fig, FIG / "e2_perplejidad_tags.png"); plt.show()
"""),
code(r"""
# Ejemplos ilustrativos (frases construidas a mano, no del corpus): log10 P por token.
ex = LM[BEST].get("examples", [])
for e in ex:
    print(f"{e['total_log10']:8.2f}  {e['sentence']}")
"""),
md(r"""
## 8. Hallazgos e interpretación

*(se completa con las cifras verificadas de las celdas anteriores)*
"""),
]

if __name__ == "__main__":
    out = build(CELLS, ROOT / "notebooks" / "evidencias" / "E2_estadistica_modelos_lenguaje.ipynb")
    print(out)
