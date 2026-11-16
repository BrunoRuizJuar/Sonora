"""Descriptive E3 statistics from full-corpus, precomputed POS counts.

No model fitting. PUNCT/SYM exclusion is a UPOS policy, not is_alpha or
spaCy's is_punct flag. Group proportions weight tokens, not documents.
"""
from collections import Counter

EXCLUDED = frozenset({'PUNCT', 'SYM', 'SPACE'})


def distributions(rows, key=None):
    """Normalize count rows within each group, retaining excluded categories."""
    counts = Counter()
    for r in rows:
        counts[(r[key] if key else 'all', r['upos'])] += int(r['count'])
    totals, lexical = Counter(), Counter()
    for (group, pos), n in counts.items():
        totals[group] += n
        if pos not in EXCLUDED:
            lexical[group] += n
    return [dict(group=g, upos=p, count=n, total=totals[g],
                 nonpunct_total=lexical[g], pct_all=100*n/totals[g],
                 pct_nonpunct=100*n/lexical[g] if p not in EXCLUDED and lexical[g] else None)
            for (g, p), n in sorted(counts.items(), key=lambda x: (str(x[0][0]), -x[1]))]


def lemma_summary(words):
    """Full-corpus type reduction and token-weighted surface/lemma changes."""
    import pyarrow.compute as pc
    keys = ['lower', 'lemma', 'upos']
    t = words.group_by(keys).aggregate([('count', 'sum')]).rename_columns(keys + ['count'])
    t = t.filter(pc.invert(pc.is_in(t['upos'], value_set=__import__('pyarrow').array(sorted(EXCLUDED)))))
    changed = pc.not_equal(t['lower'], pc.utf8_lower(t['lemma']))
    total = int(pc.sum(t['count']).as_py())
    nchanged = int(pc.sum(t.filter(changed)['count']).as_py() or 0)
    forms = len(pc.unique(t['lower']))
    lemmas = len(pc.unique(pc.utf8_lower(t['lemma'])))
    pairs = t.group_by(['lower', 'lemma']).aggregate([('count', 'sum')])
    changed_pairs = pairs.filter(pc.not_equal(pairs['lower'], pc.utf8_lower(pairs['lemma'])))
    return dict(tokens=total, changed_tokens=nchanged, changed_pct=100*nchanged/total,
                surface_types=forms, lemma_types=lemmas, reduction_pct=100*(1-lemmas/forms),
                top_changes=changed_pairs.sort_by([('count_sum', 'descending')]).slice(0, 25).to_pylist()), t
