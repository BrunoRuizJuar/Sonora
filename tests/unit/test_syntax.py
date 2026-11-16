"""E4 invariants on invented trees/counts; no claims about corpus accuracy."""
import numpy as np
import pyarrow as pa
import pytest
from sonora.nlp.syntax import audit_tree, sentence_totals, normalized


def test_arc_weighting_and_undefined_singleton_distance():
    t = pa.table(dict(n_tokens=[2,4,1],n_words=[2,4,1],depth=[1,2,0],
                      n_arcs=[1,3,0],mean_dep_dist=[1.,3.,None],root_upos=['VERB','VERB','NOUN']))
    s=normalized(sentence_totals(t).sum(axis=0))
    assert s['mean_dependency_distance']==2.5
    assert s['mean_sentence_dependency_distance']==2.
    assert s['sentences_with_arcs']==2 and s['no_arcs']==1
    assert s['nonverbal_roots']==1 and s['mean_words']==7/3
    bad=t.set_column(4,'mean_dep_dist',pa.array([1.,3.,0.]))
    with pytest.raises(ValueError,match='null policy'):
        sentence_totals(bad)


def token(i,h,dep='dep',punct=False):
    return dict(tok_i=i,head_i=h,dep=dep,is_punct=punct)


def test_tree_uses_original_positions_and_excludes_punctuation_arcs():
    r=audit_tree([token(0,5),token(5,5,'ROOT'),token(9,5),token(10,5,'punct',True)])
    assert r['issues']==[] and r['depth']==1 and r['n_arcs']==2
    assert r['mean_dep_dist']==4.5  # gaps must not be compressed to row numbers
    singleton=audit_tree([token(20,20,'ROOT')])
    assert singleton['issues']==[] and singleton['mean_dep_dist'] is None


def test_tree_detects_cycle_missing_head_and_multiple_roots():
    assert 'cycle' in audit_tree([token(0,0,'ROOT'),token(1,2),token(2,1)])['issues']
    assert 'head_outside_segment' in audit_tree([token(0,0,'ROOT'),token(1,99)])['issues']
    assert 'root_count' in audit_tree([token(0,0,'ROOT'),token(1,1,'ROOT')])['issues']
