"""E4: bounded-memory aggregation of existing sentence annotations; no spaCy run."""
from collections import Counter
from pathlib import Path
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

VERSION = 'e4-syntax-v2'
FIELDS = ['sentences', 'tokens', 'words', 'depth_sum', 'arcs', 'distance_sum',
          'sentence_distance_sum', 'sentences_with_arcs', 'no_arcs', 'no_words',
          'zero_depth', 'nonverbal_roots']


def sentence_totals(table):
    """Sufficient statistics; arc distances retain original spaCy token positions."""
    cols = {k: table[k].to_numpy(zero_copy_only=False).astype('float64')
            for k in ['n_tokens', 'n_words', 'depth', 'n_arcs', 'mean_dep_dist']}
    nt, nw, depth, arcs, dist = (cols[k] for k in cols)
    if not (np.isfinite(nt).all() and np.isfinite(nw).all() and
            np.isfinite(depth).all() and np.isfinite(arcs).all()):
        raise ValueError('Nonfinite sentence counts')
    if ((nt < nw) | (nw < 0) | (depth < 0) | (arcs < 0) | (arcs > nw)).any():
        raise ValueError('Invalid sentence counts')
    if not np.array_equal(np.isnan(dist), arcs == 0):
        raise ValueError('Distance null policy differs from arc count')
    if ((arcs > 0) & (~np.isfinite(dist) | (dist < 1))).any():
        raise ValueError('Invalid dependency distance')
    finite_dist = np.nan_to_num(dist, nan=0)
    root = table['root_upos'].to_pylist()
    return np.column_stack([np.ones(len(nt)), nt, nw, depth, arcs,
                            finite_dist * arcs, finite_dist, arcs > 0,
                            arcs == 0, nw == 0, depth == 0,
                            [p not in {'VERB', 'AUX'} for p in root]])


def normalized(values):
    r = dict(zip(FIELDS, map(float, values)))
    n = r['sentences']
    for k in ['sentences', 'tokens', 'words', 'arcs', 'sentences_with_arcs',
              'no_arcs', 'no_words', 'zero_depth', 'nonverbal_roots']:
        r[k] = int(r[k])
    r.update(mean_words=r['words']/n if n else None,
             mean_depth=r['depth_sum']/n if n else None,
             mean_dependency_distance=r['distance_sum']/r['arcs'] if r['arcs'] else None,
             mean_sentence_dependency_distance=(r['sentence_distance_sum']/r['sentences_with_arcs']
                                                if r['sentences_with_arcs'] else None))
    return r


def audit_tree(rows):
    """Check actual arcs, allowing gaps in tok_i left by removed whitespace."""
    tokens = {r['tok_i']: r for r in rows}
    issues = []
    if len(tokens) != len(rows):
        issues.append('duplicate_token_index')
    roots = [r['tok_i'] for r in rows if r['head_i'] == r['tok_i']]
    if len(roots) != 1:
        issues.append('root_count')
    if any(r['head_i'] not in tokens for r in rows):
        issues.append('head_outside_segment')
    if any((r['dep'] == 'ROOT') != (r['head_i'] == r['tok_i']) for r in rows):
        issues.append('root_label_mismatch')
    depths = {}
    for i in tokens:
        seen, cursor, hops = set(), i, 0
        while cursor in tokens:
            if cursor in seen:
                issues.append('cycle')
                break
            seen.add(cursor)
            parent = tokens[cursor]['head_i']
            if parent == cursor:
                depths[i] = hops
                break
            cursor, hops = parent, hops + 1
    arcs = [r for r in rows if not r['is_punct'] and r['head_i'] != r['tok_i']
            and r['head_i'] in tokens and not tokens[r['head_i']]['is_punct']]
    return dict(issues=sorted(set(issues)), roots=roots,
                depth=max((depths.get(r['tok_i'], 0) for r in rows if not r['is_punct']), default=0),
                n_arcs=len(arcs), mean_dep_dist=(sum(abs(r['tok_i']-r['head_i']) for r in arcs)/len(arcs)
                                               if arcs else None))


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def aggregate(root):
    """Read each of the 6317 sentence parts once, checkpointing each source shard."""
    import hashlib
    import time
    root = Path(root)
    nlp = root/'data/processed/nlp/lyrics_full_v1'
    annotation = json.loads((root/'manifests/nlp/lyrics_full_v1.json').read_text())['annotations']['spacy_sm_v1']
    assert annotation['status'] == 'complete' and annotation['tasks_remaining'] == 0
    out = nlp/'syntax'/VERSION
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    shards = sorted((nlp/'spacy_sm_v1/sentences').iterdir())
    assert len(shards) == 10
    results = []
    started = time.perf_counter()
    for shard in shards:
        parts = sorted(shard.glob('part-*.parquet'))
        docfile = nlp/'doc_stats'/f'{shard.name}.parquet'
        signature = dict(version=VERSION, code_sha256=source_hash, annotation_hash=annotation['hash'],
                         files=[(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in parts],
                         doc_stat=(docfile.stat().st_size, docfile.stat().st_mtime_ns))
        # JSON canonical round-trip keeps tuples comparable after checkpoint reload.
        signature = json.loads(json.dumps(signature))
        cache = out/f'{shard.name}.json'
        if cache.exists():
            result = json.loads(cache.read_text(encoding='utf-8'))
            if result['signature'] != signature:
                raise RuntimeError(f'Checkpoint incompatible; investigate without deleting: {cache}')
            print(f'Reusing {shard.name}', flush=True)
            results.append(result)
            continue
        metadata = pq.read_table(docfile, columns=['lyrics_id', 'tag', 'year']).to_pylist()
        from sonora.nlp.frequency import decade_of
        labels = sorted({(r['tag'], decade_of(r['year'])) for r in metadata}, key=str)
        label_index = {k: i for i, k in enumerate(labels)}
        lookup = {r['lyrics_id']: label_index[(r['tag'], decade_of(r['year']))] for r in metadata}
        assert len(lookup) == len(metadata)
        counts = Counter((r['tag'], decade_of(r['year'])) for r in metadata)
        sums = np.zeros((len(labels), len(FIELDS)))
        lengths = np.zeros((5, 4, len(FIELDS)))
        tags = ['pop', 'rap', 'rock', 'rb', 'country']
        tag_codes = np.array([tags.index(t) for t, d in labels])
        hist = {'n_words': Counter(), 'depth': Counter()}
        for part_index, p in enumerate(parts, 1):
            pf = pq.ParquetFile(p)
            m = pf.schema_arrow.metadata or {}
            assert m.get(b'sonora_annotation_hash', b'').decode() == annotation['hash']
            for batch in pf.iter_batches(batch_size=65536, columns=['lyrics_id','n_tokens','n_words',
                                           'depth','n_arcs','mean_dep_dist','root_upos']):
                table = pa.Table.from_batches([batch])
                ids = table['lyrics_id'].combine_chunks()
                if not pa.types.is_dictionary(ids.type):
                    ids = ids.dictionary_encode()
                codes = np.array([lookup[lid] for lid in ids.dictionary.to_pylist()])[ids.indices.to_numpy()]
                vals = sentence_totals(table)
                for k in range(len(FIELDS)):
                    sums[:, k] += np.bincount(codes, weights=vals[:, k], minlength=len(labels))
                nw = table['n_words'].to_numpy()
                bands = np.where(nw < 5, 0, np.where(nw < 10, 1, np.where(nw < 20, 2, 3)))
                lc = tag_codes[codes]*4 + bands
                for k in range(len(FIELDS)):
                    lengths[:, :, k] += np.bincount(lc, weights=vals[:, k], minlength=20).reshape(5,4)
                for key in hist:
                    values, freq = np.unique(table[key].to_numpy(), return_counts=True)
                    hist[key].update(dict(zip(map(int,values), map(int,freq))))
            if part_index % 100 == 0:
                print(f'{shard.name}: {part_index}/{len(parts)} parts', flush=True)
        result = dict(signature=signature, docs=len(metadata), parts=len(parts),
                      groups=[dict(tag=t, decade=d, docs=counts[(t,d)], values=list(sums[i]))
                              for i,(t,d) in enumerate(labels)],
                      length_groups=[dict(tag=t, band=b, values=list(lengths[i,j]))
                                     for i,t in enumerate(tags) for j,b in enumerate(['0–4','5–9','10–19','20+'])],
                      hist={k:dict(v) for k,v in hist.items()})
        _write(cache,result)
        results.append(result)
        print(f'Complete {shard.name}: {int(sums[:,0].sum()):,} segments', flush=True)
    groups, length_groups = {}, {}
    for result in results:
        for r in result['groups']:
            key = (r['tag'],r['decade'])
            if key not in groups: groups[key] = dict(docs=0, values=np.zeros(len(FIELDS)))
            groups[key]['docs'] += r['docs']
            groups[key]['values'] += r['values']
        for r in result['length_groups']:
            key=(r['tag'],r['band'])
            if key not in length_groups: length_groups[key]=np.zeros(len(FIELDS))
            length_groups[key] += r['values']
    total = sum((r['values'] for r in groups.values()), np.zeros(len(FIELDS)))
    assert sum(r['docs'] for r in groups.values()) == 3155772
    assert int(total[1]) == 1033733693 and int(total[0]) == 144457653
    summary = dict(version=VERSION, annotation_config=annotation['config'], annotation_hash=annotation['hash'],
                   code_sha256=source_hash, docs=3155772, parts=sum(r['parts'] for r in results),
                   global_metrics=normalized(total),
                   groups=[dict(tag=t,decade=d,docs=r['docs'],**normalized(r['values'])) for (t,d),r in groups.items()],
                   by_length=[dict(tag=t,band=b,**normalized(v)) for (t,b),v in length_groups.items()],
                   hist={}, seconds=round(time.perf_counter()-started,2))
    assert summary['parts'] == annotation['tasks_total']
    for key in ['n_words','depth']:
        h = Counter()
        for result in results: h.update({int(k):v for k,v in result['hist'][key].items()})
        assert sum(h.values()) == int(total[0])
        summary['hist'][key] = dict(sorted(h.items()))
    _write(root/'reports/nlp/lyrics_full_v1/e4_summary.json',summary)
    return summary


def examples(root):
    """Directed examples and graph audit only on first 500 lyrics of each shard."""
    root = Path(root)
    nlp = root/'data/processed/nlp/lyrics_full_v1'
    criteria = ['transitive', 'subordinate', 'coordination', 'fragment']
    candidates, issues = {}, Counter()
    total, docs, files = 0, set(), []
    for shard in sorted((nlp/'spacy_sm_v1/tokens').iterdir()):
        path = sorted(shard.glob('part-*.parquet'))[0]
        files.append(path.relative_to(root).as_posix())
        meta = pq.read_table(nlp/'doc_stats'/f'{shard.name}.parquet', columns=['lyrics_id','tag']).to_pylist()
        tag_of = {r['lyrics_id']:r['tag'] for r in meta}
        sentences = {}
        for r in pq.read_table(path).to_pylist():
            docs.add(r['lyrics_id'])
            sentences.setdefault((r['lyrics_id'],r['sent_i']),[]).append(r)
        for (lid, si), rows in sentences.items():
            total += 1
            audit = audit_tree(rows)
            issues.update(audit['issues'])
            if audit['issues'] or not 3 <= len(rows) <= 10: continue
            deps = {r['dep'] for r in rows}
            predicates = dict(transitive='nsubj' in deps and 'dobj' in deps,
                              subordinate=bool(deps & {'advcl','ccomp','relcl'}),
                              coordination='conj' in deps and 'cc' in deps,
                              fragment=not any(r['upos'] in {'VERB','AUX'} for r in rows))
            for criterion in criteria:
                key=(criterion,tag_of[lid])
                if predicates[criterion] and key not in candidates:
                    candidates[key]=dict(criterion=criterion,lyrics_id=lid,sent_i=si,
                                         line_i=rows[0]['line_i'],tag=tag_of[lid],file=files[-1],
                                         audit=audit,tokens=rows)
        print(f'Example audit: {shard.name}',flush=True)
    chosen, used_docs, used_tags = [], set(), set()
    for criterion in criteria:
        pool=[v for (c,t),v in candidates.items() if c==criterion and v['lyrics_id'] not in used_docs]
        pool.sort(key=lambda r:(r['tag'] in used_tags,r['tag'],r['lyrics_id'],r['sent_i']))
        if not pool: raise RuntimeError(f'No distinct example for {criterion} in declared selection')
        ex=pool[0]; chosen.append(ex); used_docs.add(ex['lyrics_id']); used_tags.add(ex['tag'])
    result=dict(version=VERSION, selection='first annotation part of each of 10 shards; directed, not representative',
                sample_docs=len(docs),sample_segments=total,files=files,graph_issues=dict(issues),examples=chosen)
    _write(root/'reports/nlp/lyrics_full_v1/e4_examples.json',result)
    return result


def draw_tree(example, path):
    """Dependency arrows point from head to dependent; no constituency claims."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.path import Path as PlotPath
    rows=example['tokens']; rank={r['tok_i']:i for i,r in enumerate(rows)}
    top = 0.7 + 0.2 * max((abs(rank[r['head_i']]-rank[r['tok_i']]) for r in rows), default=1)
    fig,ax=plt.subplots(figsize=(max(9,len(rows)*1.15),4.2))
    ax.axis('off')
    for i,r in enumerate(rows):
        ax.text(i,0,r['text'],ha='center',fontsize=11)
        ax.text(i,-0.32,r['upos'],ha='center',fontsize=8,color='#52514e')
        ax.text(i,-0.58,str(r['tok_i']),ha='center',fontsize=7)
        if r['head_i']==r['tok_i']:
            ax.annotate('ROOT',xy=(i,0.22),xytext=(i,top+0.05),ha='center',
                        arrowprops={'arrowstyle':'->'},fontsize=9)
            continue
        h=rank[r['head_i']]; span=abs(h-i)
        height=0.5+0.2*span
        curve=PlotPath([(h,0.22),(h,height),(i,height),(i,0.22)],
                       [PlotPath.MOVETO,PlotPath.CURVE4,PlotPath.CURVE4,PlotPath.CURVE4])
        ax.add_patch(FancyArrowPatch(path=curve,arrowstyle='-|>',mutation_scale=10,color='#2a78c4'))
        ax.text((h+i)/2,0.08+0.75*height,r['dep'],ha='center',fontsize=8,
                bbox={'facecolor':'white','edgecolor':'none','alpha':0.85})
    ax.set(xlim=(-0.7,len(rows)-0.3),ylim=(-0.9,top+0.4))
    ax.set_title(f"{example['criterion']} · {example['tag']} · flechas cabeza → dependiente",loc='left')
    fig.text(0.05,0.02,f"{example['lyrics_id']} · sent_i={example['sent_i']} · line_i={example['line_i']} · índices originales",fontsize=8)
    from sonora.viz import save
    save(fig,Path(path))
    return fig
