"""E5 validation-only qualitative analysis in one selected SGNS space.

Sample size and scope accompany every result. Static word embeddings do not
change by period: only their observed context averages are compared.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from sonora.nlp.semantic_models import load_model, load_vocab, validation_sample
from sonora.nlp.semantics import pool
from sonora.storage.runs import write_json_atomic


def analyze(cache: Path, models: Path, reports: Path, figures: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA

    selected = json.loads((models / 'trained.json').read_text(encoding='utf-8'))
    model = load_model(selected['sgns']['path'])
    rows = load_vocab(cache)
    lookup = {r['word']: (r['index'], r['idf']) for r in rows}
    vectors = np.array([model.wv[r['word']] for r in rows], dtype=np.float32)
    sample = validation_sample(cache)
    valid, pooled = [], []
    for row in sample:
        vector, available = pool(row['words'], lookup, vectors)
        if available:
            valid.append(row)
            pooled.append(vector)
    x = np.array(pooled)
    if len(x) < 3:
        raise ValueError('Insufficient validation vectors for projection')
    pca = PCA(n_components=2, svd_solver='full', random_state=42)
    xy = pca.fit_transform(x)
    figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    for tag in sorted({r['tag'] or 'sin tag' for r in valid}):
        ix = [i for i, row in enumerate(valid) if (row['tag'] or 'sin tag') == tag]
        ax.scatter(xy[ix, 0], xy[ix, 1], s=9, alpha=.45, label=f'{tag} (n={len(ix)})')
    ax.set(xlabel=f'PC1 ({pca.explained_variance_ratio_[0]:.1%})',
           ylabel=f'PC2 ({pca.explained_variance_ratio_[1]:.1%})',
           title=f'E5 · muestra de validación: {len(x)} letras\nPCA de embeddings agregados; no mide relevancia')
    ax.legend(markerscale=2)
    fig.tight_layout()
    fig.savefig(figures / 'pca_validation.png', dpi=160)
    plt.close(fig)
    concepts = {}
    for concept in ('love', 'home', 'money', 'war', 'freedom'):
        if concept not in model.wv:
            concepts[concept] = {'available': False}
            continue
        groups = defaultdict(lambda: {'occurrences': 0, 'documents': 0,
                                      'context_words': Counter(), 'vector_sum': np.zeros(vectors.shape[1]),
                                      'examples': []})
        for row in sample:
            terms = row['words']
            positions = [i for i, w in enumerate(terms) if w == concept]
            if not positions:
                continue
            contexts = []
            for i in positions:
                contexts.extend(w for j, w in enumerate(terms[max(0, i-5):i+6], max(0, i-5))
                                if j != i and w in lookup and w != concept)
            if not contexts:
                continue
            context, available = pool(contexts, lookup, vectors)
            if not available:
                continue
            year = row['year']
            decade = str(year//10*10) if year is not None and 1900 <= year <= 2022 else 'sin año válido'
            for label in (f"tag:{row['tag']}", f'decade:{decade}'):
                group = groups[label]
                group['occurrences'] += len(positions)
                group['documents'] += 1
                group['context_words'].update(contexts)
                group['vector_sum'] += context  # equal weight per lyric, not repeated chorus
                if len(group['examples']) < 2:
                    i = positions[0]
                    group['examples'].append({'lyrics_id': row['lyrics_id'], 'word_index': i,
                                               'context': terms[max(0, i-5):i+6]})
        serialized, centroids = {}, {}
        for label, group in groups.items():
            supported = group['documents'] >= 10 and group['occurrences'] >= 20
            vector = group['vector_sum']
            norm = np.linalg.norm(vector)
            if supported and norm:
                centroids[label] = vector/norm
            serialized[label] = {k: v for k, v in group.items() if k not in {'vector_sum', 'context_words'}}
            serialized[label]['top_context_words'] = group['context_words'].most_common(15)
            serialized[label]['support_sufficient'] = supported
        contrasts = []
        labels = sorted(centroids)
        for i, left in enumerate(labels):
            for right in labels[i+1:]:
                if left.split(':')[0] == right.split(':')[0]:
                    contrasts.append({'left': left, 'right': right,
                                      'context_centroid_cosine': float(centroids[left] @ centroids[right])})
        concepts[concept] = {'available': True, 'static_word_neighbors': model.wv.most_similar(concept, topn=10),
                             'groups': serialized, 'contrasts': contrasts,
                             'limits': 'descriptive context averages; static word vector is identical in every group'}
    write_json_atomic(reports / 'e5_analysis.json', {
        'scope': 'bottom-SHA256 sample of <=2000 validation lyrics; models fitted on full train',
        'sample_ids': [r['lyrics_id'] for r in sample], 'n_projected': len(x),
        'projection': {'method': 'PCA', 'svd_solver': 'full', 'n_components': 2, 'random_state': 42,
                       'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
                       'fit_scope': 'validation visualization sample only',
                       'mean': pca.mean_.tolist(), 'components': pca.components_.tolist(),
                       'points': [{'lyrics_id': row['lyrics_id'], 'tag': row['tag'], 'xy': point.tolist()}
                                  for row, point in zip(valid, xy)]},
        'concepts': concepts, 'minimum_context_support': {'documents': 10, 'occurrences': 20},
        'limits': ['sample is not the full corpus', 'no causal or significance claims',
                   'source year/tag and repetition can confound contexts',
                   'similarity may reflect thematic relation or antonymy, not equivalence',
                   'no recommendation evaluation or test judgments'],
    })
