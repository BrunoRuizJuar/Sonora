"""E3 normalization and lemmatization on synthetic counts only."""
import pyarrow as pa
from sonora.nlp.morphology import distributions, lemma_summary


def test_group_denominators_and_unknown_decade():
    rows = [dict(decade=None, upos='NOUN', count=3),
            dict(decade=None, upos='PUNCT', count=1),
            dict(decade=2000, upos='VERB', count=2),
            dict(decade=None, upos='NOUN', count=2)]
    r = distributions(rows, 'decade')
    noun = next(x for x in r if x['upos'] == 'NOUN')
    assert noun['count'] == 5 and noun['total'] == 6
    assert noun['pct_nonpunct'] == 100
    assert next(x for x in r if x['upos'] == 'PUNCT')['pct_nonpunct'] is None
    assert sum(x['count'] for x in r) == 8


def test_lemma_counts_merge_splits_and_ignore_case():
    t = pa.table(dict(lower=['dogs', 'dogs', 'i', '.', 'dog'],
                      lemma=['dog', 'dog', 'I', '.', 'dog'],
                      upos=['NOUN', 'NOUN', 'PRON', 'PUNCT', 'NOUN'],
                      count=[2, 3, 4, 10, 1]))
    s, _ = lemma_summary(t)
    assert s['tokens'] == 10 and s['changed_tokens'] == 5
    assert s['surface_types'] == 3 and s['lemma_types'] == 2
    assert s['top_changes'][0]['count_sum'] == 5
