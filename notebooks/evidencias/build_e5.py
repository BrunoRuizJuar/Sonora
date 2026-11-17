"""Build and execute E5 evidence from completed real artifacts; no model fitting."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbbuild import ROOT, build, md, code

CELLS = [md('''
# Evidencia 5 — Semántica

SONORA · E5-01…05 · `lyrics_full_v1` / `e5-surface-v2`.
Resultados reales del corpus completo, con modelos ajustados sólo en train.
Validation selecciona; test se transforma y se comprueba numéricamente, sin
evaluación de relevancia. La muestra de PCA/contextos es de 2 000 letras de
validación y no sustituye el entrenamiento completo. Este notebook no reentrena.
'''), code('''
import json
from pathlib import Path
from collections import Counter
from IPython.display import display, Markdown, Image
ROOT = Path.cwd()
REPORTS = ROOT / 'reports/nlp/lyrics_full_v1'
MODELS = ROOT / 'artifacts/models/lyrics_full_v1/e5-surface-v2'
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def show(rows):
    if not rows:
        print('Sin resultados con soporte suficiente.')
        return
    keys = list(rows[0])
    text = '| ' + ' | '.join(keys) + ' |\\n| ' + ' | '.join(['---']*len(keys)) + ' |\\n'
    text += '\\n'.join('| ' + ' | '.join(str(row[k]).replace('|', '/') for k in keys) + ' |' for row in rows)
    display(Markdown(text))
audit = read(REPORTS/'e5_verification.json')
analysis = read(REPORTS/'e5_analysis.json')
semantic = read(REPORTS/'e5_embedding_retrieval.json')
lexical = read(REPORTS/'e5_tfidf_retrieval.json')
assert audit['unique_ids'] == audit['counts']['docs'] == 3155772
assert audit['space_id'] == semantic['space_id']
assert audit['max_embedding_norm_error'] < 1e-5
assert audit['max_topic_sum_error'] < 1e-5
print('Auditoría real:', audit['verified_utc'])
print('Espacio común:', audit['space_id'])
show([{'split': s, 'letras': audit['counts']['docs_'+s], 'cobertura tokens': audit['token_coverage_by_split'][s]} for s in ('train','validation','test')])
print('No disponibles:', audit['counts']['embedding_unavailable'])
print('Errores máximos norma/suma:',audit['max_embedding_norm_error'],audit['max_topic_sum_error'])
print('Checkpoints con hashes comprobados:',audit['checkpoint_counts'])
'''), md('## 1. Entrenamiento propio y selección (E5-01)'), code('''
selection = read(MODELS/'sgns_selection.json')
show([{'ventana': c['window'], 'objetivo validation': c['mean_log_objective'], 'pares': c['positive_pairs']} for c in selection['candidates']])
print('Ventana seleccionada:', selection['selected']['window'])
print('Criterio:',selection['criterion'])
print('Dimensión 128; tres épocas completas de train; cuatro workers; TF-IDF sublineal y L2.')
'''), md('## 2. PCA de la muestra explícita de validación (E5-02)'), code('''
p = analysis['projection']
assert len(set(analysis['sample_ids'])) == analysis['n_projected'] == 2000
print({k:p[k] for k in ('method','svd_solver','n_components','random_state','fit_scope','explained_variance_ratio')})
print('Varianza acumulada:',sum(p['explained_variance_ratio']))
print('Soportes por tag:',dict(Counter(r['tag'] for r in p['points'])))
print('Los 2 000 IDs, coordenadas, media y componentes se conservan en e5_analysis.json.')
display(Image(filename=str(ROOT/'reports/figures/E5/pca_validation.png')))
'''), md('## 3. Conceptos y contextos compartidos (E5-03/04/05)'), code('''
for word, result in analysis['concepts'].items():
    display(Markdown('### '+word))
    show([{'vecino': w, 'coseno': c} for w,c in result['static_word_neighbors']])
    show([{'grupo': label, 'letras': g['documents'], 'ocurrencias': g['occurrences'], 'soporte suficiente': g['support_sufficient']} for label,g in result['groups'].items()])
    show(result['contrasts'])
    for label,g in result['groups'].items():
        if label.startswith('tag:'):
            print(label, g['examples'])
print('Umbral:',analysis['minimum_context_support'])
print('El vector estático no cambia; cambian contextos agregados en un mismo espacio.')
'''), md('## 4. Recuperación exacta y contextos para revisión asistida (E5-01)'), code('''
assert semantic['available_candidates'] == 2208832
assert [q['query']['lyrics_id'] for q in semantic['queries']] == [q['query']['lyrics_id'] for q in lexical['queries']]
for q, base in zip(semantic['queries'], lexical['queries']):
    display(Markdown('### '+q['query']['title']+' · '+q['query']['lyrics_id']))
    show([{'modelo':'SGNS', 'rango':i+1, 'titulo':r['title'], 'artista':r['artist'], 'ID':r['lyrics_id'], 'coseno':r['cosine']} for i,r in enumerate(q['neighbors'])])
    show([{'modelo':'TF-IDF', 'rango':i+1, 'titulo':r['title'], 'ID':r['lyrics_id'], 'coseno':r['cosine']} for i,r in enumerate(base['neighbors'])])
    print('Vecinos comunes:',q['shared_neighbor_ids_with_tfidf'])
for row in audit['retrieval_excerpt_review_material']:
    print(row['lyrics_id'], row['title'], row['excerpt_scope'])
    print(' '.join(row['words']))
print('Extractos de revisión dirigida, no muestra representativa ni juicios gold.')
'''), md('## 5. LDA y resultado temático limitado'), code('''
lda = read(MODELS/'lda/lda_selection.json')
show([{k:v for k,v in c.items() if k not in ('path','top_words')} for c in lda['candidates']])
show([{'topico':i, 'terminos top10':', '.join(words), 'masa media train':audit['topic_mean_by_split']['train'][i]} for i,words in enumerate(lda['selected']['top_words'])])
print('Estabilidad:',lda['seed_stability']['method'])
print('Jaccard medio:',lda['seed_stability']['mean_jaccard'])
show(lda['seed_stability']['matches'])
print('Masa train tópicos 0/4/14:',sum(audit['topic_mean_by_split']['train'][i] for i in (0,4,14)))
print('No se incorporan tópicos al ranking; faltan ablación y juicios de validación.')
''')]

review = (ROOT/'docs/E5_RESULTADOS.md').read_text(encoding='utf-8')
review = review.replace('../reports/', '../../reports/').replace('(E5_METODO.md)', '(../../docs/E5_METODO.md)').replace('(E5_RECOMMENDATIONS.md)', '(../../docs/E5_RECOMMENDATIONS.md)').replace('../TODO-human.md', '../../TODO-human.md')
CELLS.append(md('## 6. Interpretación asistida, límites y matriz de requisitos\n\n'+review))

if __name__ == '__main__':
    print(build(CELLS, ROOT/'notebooks/evidencias/E5_semantica.ipynb'))
