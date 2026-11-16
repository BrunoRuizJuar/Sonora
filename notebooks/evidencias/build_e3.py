"""Build and execute E3 using existing complete annotation; no reannotation.

Run: .venv\\Scripts\\python.exe notebooks\\evidencias\\build_e3.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbbuild import ROOT, build, md, code

CELLS = [md(r"""
# Evidencia 3 — Morfosintaxis: categorías gramaticales y lematización

**SONORA · PLN · E3-01 a E3-04 · corpus completo `lyrics_full_v1`.**

Se reutiliza la anotación de las 3 155 772 letras canónicas, no sólo la demo FMA.
spaCy 3.8.18, `en_core_web_sm` 3.8.0, sin NER; vista `lyrics_analysis`.
Los saltos de verso fuerzan fronteras; el parser puede subdividir un verso.
Se preserva la superficie original; formas g-dropping admitidas se analizan mediante
texto sombra de igual longitud (`runnin'` → `running`) conservando índices.
No se corrigen las predicciones después de observarlas.

Las métricas son descriptivas sobre **todos los splits**. No se entrenan modelos,
no se eligen hiperparámetros y no se evalúa recuperación con test.
`frequency/word_pos.parquet` agrega `(split, lower, lemma, upos)`;
`group_pos.parquet` agrega `(split, tag, decade, upos)` sobre la misma anotación.
`doc_stats/` aporta los tamaños documentales. Los tags son etiquetas de la fuente,
no géneros validados; `year` tampoco certifica fecha de composición.

**Denominadores:** todos los tokens spaCy no espaciales; alternativamente todos salvo
UPOS `PUNCT`, `SYM`, `SPACE`. Esta segunda política conserva números, clíticos y `X`:
no equivale a palabras alfabéticas ni al tokenizador regex de E2. No se retiran
stopwords ni vocablos. Las proporciones ponderan tokens: las letras largas y estribillos
repetidos pesan más. No representan la letra media ni causalidad entre género y gramática.
"""), code(r"""
import json, sys
from pathlib import Path
from collections import Counter
import numpy as np
import pyarrow as pa, pyarrow.compute as pc, pyarrow.dataset as ds, pyarrow.parquet as pq
import matplotlib.pyplot as plt
import yaml
from IPython.display import display, Markdown
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT/'packages/sonora/src'))
from sonora import viz
from sonora.nlp.morphology import distributions, lemma_summary, EXCLUDED
from sonora.nlp.frequency import decade_of
viz.apply_style()
NLP = ROOT/'data/processed/nlp/lyrics_full_v1'
FIG = ROOT/'reports/figures/E3'
manifest = json.loads((ROOT/'manifests/nlp/lyrics_full_v1.json').read_text(encoding='utf-8'))
annotation = manifest['annotations']['spacy_sm_v1']
assert annotation['status'] == 'complete' and annotation['tasks_remaining'] == 0
words = pq.read_table(NLP/'frequency/word_pos.parquet')
groups = pq.read_table(NLP/'frequency/group_pos.parquet').to_pylist()
docs = ds.dataset(NLP/'doc_stats').to_table(columns=['lyrics_id','tag','year'])
assert docs.num_rows == 3155772
def show(rows):
    if not rows: return
    cols = list(rows[0])
    def val(x):
        if x is None: return '—'
        if isinstance(x, float): return f'{x:.3f}'
        return str(x).replace('|', r'\|').replace('\n', ' / ')
    display(Markdown('\n'.join(['| '+' | '.join(cols)+' |', '|'+'---|'*len(cols)] +
                              ['| '+' | '.join(val(r[c]) for c in cols)+' |' for r in rows])))
global_pos = distributions(groups)
N = sum(r['count'] for r in global_pos)
assert N == int(pc.sum(words['count']).as_py()) == 1033733693
print('Configuración:', annotation['config'])
print('Letras:', docs.num_rows, '| tokens:', N)
"""), md(r"""
## 1. Distribución gramatical completa (E3-02)

Las dos columnas porcentuales usan universos distintos, declarados en cada fila.
Los excluidos se conservan en la tabla y carecen de porcentaje en el segundo universo.
"""), code(r"""
show(global_pos)
assert abs(sum(r['pct_all'] for r in global_pos)-100) < 1e-8
assert abs(sum(r['pct_nonpunct'] or 0 for r in global_pos)-100) < 1e-8
fig, ax = plt.subplots(figsize=(9,4))
ax.bar([r['upos'] for r in global_pos], [r['pct_all'] for r in global_pos], color=viz.SEQUENTIAL)
ax.set(ylabel='% de todos los tokens', title='Categorías gramaticales · corpus completo')
ax.tick_params(axis='x', rotation=45)
viz.save(fig, FIG/'pos_global.png'); plt.show()
"""), md(r"""
## 2. Comparaciones por tag y década (E3-03)

Conteos documentales completos y porcentajes por token sin `PUNCT/SYM/SPACE`.
Década = `year // 10 * 10` sólo entre 1900 y 2022; los demás valores se agrupan
como desconocidos, sin imputación. Las décadas pequeñas se muestran en las tablas;
el gráfico temporal usa las de al menos 1 000 letras para reducir inestabilidad descriptiva.
No se interpreta una tendencia temporal como evolución de los mismos artistas:
cambian composición, cobertura y mezcla de tags del dataset.
"""), code(r"""
doc_tags = Counter(docs['tag'].to_pylist())
doc_dec = Counter(decade_of(y) for y in docs['year'].to_pylist())
tag_pos = distributions(groups, 'tag')
dec_pos = distributions(groups, 'decade')
for name, counts, rows in [('tag',doc_tags,tag_pos), ('década',doc_dec,dec_pos)]:
    sizes = []
    for g in sorted(counts, key=lambda x: str(x)):
        selected = [r for r in rows if r['group']==g]
        total = sum(r['count'] for r in selected)
        nonpunct = sum(r['count'] for r in selected if r['upos'] not in EXCLUDED)
        sizes.append({'grupo':g, 'letras':counts[g], '% letras':100*counts[g]/docs.num_rows,
                      'tokens':total, 'tokens sin puntuación/símbolos':nonpunct})
    print(name); show(sizes)
    assert sum(r['tokens'] for r in sizes) == N
    assert sum(counts.values()) == docs.num_rows
show(tag_pos); show(dec_pos)
pos_order = [r['upos'] for r in global_pos if r['upos'] not in EXCLUDED]
tags = [t for t in viz.TAG_ORDER if t in doc_tags]
matrix = np.array([[next((r['pct_nonpunct'] for r in tag_pos if r['group']==t and r['upos']==p),0)
                    for p in pos_order] for t in tags])
fig, ax = plt.subplots(figsize=(12,4))
im = ax.imshow(matrix, cmap='Blues', aspect='auto')
ax.set_xticks(range(len(pos_order)),pos_order,rotation=45); ax.set_yticks(range(len(tags)),tags)
ax.set_title('POS por tag · % de tokens sin PUNCT/SYM/SPACE')
fig.colorbar(im, ax=ax, label='% dentro del tag')
viz.save(fig, FIG/'pos_tags.png'); plt.show()
decades = sorted(d for d in doc_dec if d is not None and doc_dec[d]>=1000)
fig, ax = plt.subplots(figsize=(9,4))
for p in ['NOUN','VERB','PRON','PROPN','ADJ','AUX']:
    ax.plot(decades,[next((r['pct_nonpunct'] for r in dec_pos if r['group']==d and r['upos']==p),0)
                    for d in decades], marker='o', label=p)
ax.set(title='POS por década · grupos con ≥ 1 000 letras', xlabel='Década de year', ylabel='% sin PUNCT/SYM/SPACE')
ax.legend(ncol=3); viz.save(fig, FIG/'pos_decadas.png'); plt.show()
spread = []
for p in pos_order:
    rows = [r for r in tag_pos if r['upos']==p]
    lo, hi = min(rows,key=lambda r:r['pct_nonpunct']),max(rows,key=lambda r:r['pct_nonpunct'])
    spread.append({'POS':p,'mínimo tag':lo['group'],'mínimo %':lo['pct_nonpunct'],
                   'máximo tag':hi['group'],'máximo %':hi['pct_nonpunct'],
                   'diferencia pp':hi['pct_nonpunct']-lo['pct_nonpunct']})
show(sorted(spread,key=lambda r:-r['diferencia pp']))
# Temporal comparison within tag: separates some composition effects, not all confounding.
eligible = [d for d in decades if d >= 1970]
endpoints = [eligible[0],eligible[-1]]
within = []
for tag in tags:
    for dec in endpoints:
        sub = [r for r in groups if r['tag']==tag and r['decade']==dec]
        rr = distributions(sub)
        within.append({'tag':tag,'década':dec,'tokens sin puntuación':sum(r['count'] for r in rr if r['upos'] not in EXCLUDED),
                       **{p:next((r['pct_nonpunct'] for r in rr if r['upos']==p),0) for p in ['NOUN','VERB','PRON','PROPN']}})
show(within)
"""), md(r"""
## 3. Lematización: reducción y ambigüedad (E3-01)

Se compara forma en minúsculas con lema en minúsculas para evitar contar `i → I`
como cambio morfológico. Se excluyen las mismas tres categorías UPOS.
Los tipos son cadenas únicas, no parejas `(forma, POS)`. El cociente de tipos no es
una medida de exactitud: la polisemia, el slang y errores también cambian los lemas.
Un lema puede coincidir con formas superficiales de otras palabras.
"""), code(r"""
lemmas, merged = lemma_summary(words)
show([{k:v for k,v in lemmas.items() if k!='top_changes'}])
show(lemmas['top_changes'])
lemma_by_pos = []
for p in pos_order:
    t = merged.filter(pc.equal(merged['upos'],p))
    n = int(pc.sum(t['count']).as_py() or 0)
    changed = t.filter(pc.not_equal(t['lower'],pc.utf8_lower(t['lemma'])))
    nc = int(pc.sum(changed['count']).as_py() or 0)
    lemma_by_pos.append({'POS':p,'tokens':n,'tokens con cambio':nc,'% con cambio':100*nc/n if n else 0})
show(lemma_by_pos)
assert sum(r['tokens'] for r in lemma_by_pos)==lemmas['tokens']
assert sum(r['tokens con cambio'] for r in lemma_by_pos)==lemmas['changed_tokens']
targets = ["n't","'s","ca","wo","gon","na","ridin'","riding","runnin'","yeah","oh","yo","love"]
ambiguous = merged.filter(pc.is_in(merged['lower'],value_set=pa.array(targets)))
show(ambiguous.sort_by([('count','descending')]).slice(0,70).to_pylist())
vocables = set(yaml.safe_load((ROOT/'config/vocables.yaml').read_text(encoding='utf-8'))['vocables'])
vt = merged.filter(pc.is_in(merged['lower'],value_set=pa.array(sorted(vocables))))
vpos = vt.group_by('upos').aggregate([('count','sum')]).sort_by([('count_sum','descending')])
print('Tokens spaCy cuya forma coincide con la lista de vocablos (no todos son usos vocalizados):')
show(vpos.to_pylist())
"""), md(r"""
## 4. Auditoría cualitativa trazable (E3-04)

Selección **dirigida, no aleatoria ni representativa**: primer archivo de anotación
(hasta 500 letras) de cada uno de los diez shards. Se conserva el primer ejemplo por
criterio, hasta diez, con contexto de oración y posiciones originales. No se
vuelven a etiquetar los ejemplos. Los conteos de esta selección no se extrapolan.
Los textos son fragmentos breves del corpus local; los IDs y archivo permiten recuperar
la letra. `line_i`, `sent_i` y `tok_i` empiezan en cero.
"""), code(r"""
criteria = {
 'negación contraída': lambda r:r['lower']=="n't",
 'posesivo/auxiliar ambiguo': lambda r:r['lower']=="'s",
 'slang gonna': lambda r:r['lower']=='gon',
 'g-dropping normalizado': lambda r:r['gdrop_normalized'],
 'ridin': lambda r:r['lower'].startswith('ridin'),
 'vocablo PROPN': lambda r:r['lower'] in {'oh','yeah','ooh','la','na'} and r['upos']=='PROPN',
 'interjección': lambda r:r['upos']=='INTJ',
 'nombre propio': lambda r:r['upos']=='PROPN' and r['lower'] not in vocables,
 'fragmento sin verbo': lambda r:False,
}
examples = {}; sample_docs = set(); inspected_parts=[]
for shard in sorted((NLP/'spacy_sm_v1/tokens').iterdir()):
    part = sorted(shard.glob('part-*.parquet'))[0]
    inspected_parts.append(str(part.relative_to(ROOT)))
    table = pq.read_table(part)
    sample_docs.update(table['lyrics_id'].to_pylist())
    rows = table.to_pylist()
    # First matching token per criterion, deterministic file and row order.
    for r in rows:
        for criterion, predicate in criteria.items():
            if criterion not in examples and predicate(r):
                sentence = [x for x in rows if x['lyrics_id']==r['lyrics_id'] and x['sent_i']==r['sent_i']]
                examples[criterion] = dict(criterion=criterion, file=str(part.relative_to(ROOT)),
                    lyrics_id=r['lyrics_id'],sent_i=r['sent_i'],line_i=r['line_i'],tok_i=r['tok_i'],
                    text=r['text'],upos=r['upos'],lemma=r['lemma'],gdrop=r['gdrop_normalized'],
                    context=' '.join(x['text'] for x in sentence)[:220],
                    annotation=[{k:x[k] for k in ['tok_i','text','upos','lemma']} for x in sentence[:30]])
    if 'fragmento sin verbo' not in examples:
        sentences = {}
        for r in rows: sentences.setdefault((r['lyrics_id'],r['sent_i']),[]).append(r)
        for (lid, si), sent in sentences.items():
            if 2 <= len(sent) <= 6 and not any(r['upos'] in {'VERB','AUX'} for r in sent):
                r=sent[0]
                examples['fragmento sin verbo']=dict(criterion='fragmento sin verbo',file=str(part.relative_to(ROOT)),
                    lyrics_id=lid,sent_i=si,line_i=r['line_i'],tok_i=r['tok_i'],text=r['text'],upos=r['upos'],
                    lemma=r['lemma'],gdrop=r['gdrop_normalized'],context=' '.join(x['text'] for x in sent),
                    annotation=[{k:x[k] for k in ['tok_i','text','upos','lemma']} for x in sent])
                break
    del table, rows
print('Selección:',len(sample_docs),'letras en',len(inspected_parts),'partes; criterios encontrados:',len(examples))
for criterion, ex in examples.items():
    print('\n',criterion, '|',ex['lyrics_id'],'| línea',ex['line_i'],'| oración',ex['sent_i'])
    print(ex['context']); print('Archivo:',ex['file'])
    show(ex['annotation'])
missing = sorted(set(criteria)-set(examples))
print('Criterios no encontrados en la selección:',missing)
summary = dict(version='e3-morphology-v1', docs=docs.num_rows,tokens=N,global_pos=global_pos,
               lemma=lemmas, tag_spread=spread, sample_docs=len(sample_docs),sample_parts=inspected_parts,
               examples=list(examples.values()),missing_criteria=missing)
OUT = ROOT/'reports/nlp/lyrics_full_v1'
OUT.mkdir(parents=True,exist_ok=True)
tmp = OUT/'e3_summary.json.tmp'
tmp.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
tmp.replace(OUT/'e3_summary.json')
"""), md(r"""
## 5. Lectura lingüística y límites

- `PRON` permite examinar interlocución y persona; `VERB/AUX` acciones y modalidad;
  `NOUN/PROPN` referencias nominales. Estas categorías no determinan por sí solas temas,
  emociones ni calidad de una recomendación. Las diferencias máximas entre tags se
  cuantifican en puntos porcentuales arriba, con tamaños y denominadores explícitos.
- Las contracciones separan clíticos: `n't` puede lematizarse como `not`; `ca` es
  una pieza de `can't`, no necesariamente una palabra autónoma defectuosa. `'s` requiere
  contexto para distinguir posesivo de auxiliar. `gon`/`na` pueden proceder de `gonna`;
  por eso no debe interpretarse cada `na` como una sílaba de estribillo.
- El texto sombra reduce diferencias ortográficas de g-dropping sin garantizar un lema
  correcto. Las predicciones de `ridin` y otros ejemplos deben leerse junto al contexto:
  normalización gráfica y desambiguación morfológica son tareas distintas.
- Un vocablo repetido etiquetado `PROPN` puede reflejar desajuste de dominio del modelo;
  un nombre propio verdadero también puede repetir letras. La tabla de formas ambiguas
  y los contextos permiten discutir casos, sin reclasificar automáticamente todos los tokens.
- Los fragmentos sin verbo son compatibles con letras, títulos y respuestas breves;
  no prueban por sí solos un error. Tampoco una oración por verso equivale necesariamente
  a una oración gramatical completa. E4 profundizará en dependencias.
- La reducción de tipos por lematización y su frecuencia por POS describen compresión,
  no precisión. No existe aquí un conjunto de referencia humana: **no se estima accuracy**.
  La selección dirigida sirve para encontrar mecanismos de error, no su prevalencia.
- Los porcentajes temporales están afectados por metadatos ausentes, tamaños desiguales
  y composición por tag/artista. La comparación temporal dentro de cada tag es una
  comprobación descriptiva adicional; no elimina todos esos factores.

**Reproducibilidad:** ejecutar `build_e3.py` desde el venv del proyecto. Se usan los
agregados completos de `e2_frequency.py pos-lexicon` y la anotación ya terminada;
no se modifica `data/raw`, no se reentrena spaCy. Figuras en `reports/figures/E3/`;
resumen y procedencia de ejemplos en `reports/nlp/lyrics_full_v1/e3_summary.json`.
""")]

if __name__ == '__main__':
    print(build(CELLS, ROOT/'notebooks/evidencias/E3_morfosintaxis.ipynb'))
