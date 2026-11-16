import math
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from sonora.nlp.semantics import Documents, fit_baseline, pool, prepare, tfidf, words


def test_surface_and_pooling():
    assert words("DON’T ridin' 123 café") == ["don't", 'ridin', 'café']
    vocab = {'a': (0, 1.), 'b': (1, 2.)}
    vectors = np.array([[1., 0.], [0., 1.]], dtype=np.float32)
    idx, weights = tfidf(['a', 'a', 'b'], vocab)
    result, available = pool(['a', 'a', 'b'], vocab, vectors)
    assert available
    assert np.allclose(result, weights)
    assert np.isclose(result[0]/result[1], (1+math.log(2))/2)
    empty, available = pool(['unseen'], vocab, vectors)
    assert not available and not empty.any()


def fixture(root: Path):
    corpus = root / 'data/processed/lyrics/lyrics_full_v1/corpus'
    corpus.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([
        {'lyrics_id': 'a', 'lyrics_analysis': 'love home', 'tag': 'pop', 'year': 2000, 'title': 'A', 'artist': 'X'},
        {'lyrics_id': 'b', 'lyrics_analysis': 'love road', 'tag': 'pop', 'year': 2010, 'title': 'B', 'artist': 'Y'},
        {'lyrics_id': 'c', 'lyrics_analysis': 'validationonly love', 'tag': 'rap', 'year': 2020, 'title': 'C', 'artist': 'Z'},
        {'lyrics_id': 'd', 'lyrics_analysis': 'testonly love', 'tag': 'rap', 'year': None, 'title': 'D', 'artist': 'W'},
    ]), corpus / 'shard.parquet')
    splits = root / 'data/processed/splits/lyrics_full_v1'
    splits.mkdir(parents=True)
    pq.write_table(pa.table({'lyrics_id': ['d', 'b', 'a', 'c'],
                            'split': ['test', 'train', 'train', 'validation']}), splits / 'lyrics_splits.parquet')


def test_fit_train_only_resume_and_input_guard(tmp_path):
    import pytest
    fixture(tmp_path)
    cache = prepare(tmp_path)
    baseline = fit_baseline(cache, min_df=1)
    rows = pq.read_table(baseline / 'vocabulary.parquet').to_pylist()
    assert {r['word'] for r in rows} == {'home', 'road'}  # love exceeds max_df
    assert all(np.isclose(r['idf'], math.log(3/2)+1) for r in rows)
    assert list(Documents(cache, 'validation')) == [['validationonly', 'love']]
    assert prepare(tmp_path) == cache
    source = tmp_path / 'data/processed/lyrics/lyrics_full_v1/corpus/shard.parquet'
    source.write_bytes(source.read_bytes() + b'changed')
    with pytest.raises(RuntimeError, match='Incompatible checkpoint'):
        prepare(tmp_path)


def test_native_models_and_export_resume(tmp_path):
    """Synthetic integration: candidate selection, model reload, sparse/vector IDs."""
    import json
    from sonora.nlp.semantic_models import train_sgns, train_lda, validation_sample
    from sonora.nlp.semantic_export import export
    from sonora.nlp.semantic_retrieval import retrieve_baseline, retrieve_embeddings
    from sonora.storage.runs import write_json_atomic

    fixture(tmp_path)
    source = tmp_path / 'data/processed/lyrics/lyrics_full_v1/corpus/shard.parquet'
    rows = pq.read_table(source).to_pylist()
    rows[0]['lyrics_analysis'] = 'love home ' * 1000
    rows[1]['lyrics_analysis'] = 'love road ' * 1000
    rows[2]['lyrics_analysis'] = 'home road home'
    pq.write_table(pa.Table.from_pylist(rows), source)
    cache = prepare(tmp_path)
    fit_baseline(cache, min_df=1)
    sample = validation_sample(cache)
    models = tmp_path / 'artifacts/test-models'
    sgns = train_sgns(cache, models, sample, epochs=1)
    lda = train_lda(cache, models, sample)
    assert sgns['positive_pairs'] == 6
    epoch = Path(sgns['path']).with_suffix('.json')
    assert json.loads(epoch.read_text())['trained_effective_and_raw_words'][0] > 0
    assert sgns == train_sgns(cache, models, sample, epochs=1)
    assert lda == train_lda(cache, models, sample)
    write_json_atomic(models / 'trained.json', {'sgns': sgns, 'lda': lda})
    out = export(cache, models)
    result = pq.read_table(out / 'shard.parquet').to_pylist()
    assert len(result) == 4
    assert result[3]['lyrics_id'] == 'd' and result[3]['split'] == 'test'
    assert not result[3]['embedding_available'] and not result[3]['topics_available']
    assert all(np.isclose(np.linalg.norm(r['embedding']), 1) for r in result[:3])
    before = (out / 'shard.parquet').read_bytes()
    export(cache, models)
    assert (out / 'shard.parquet').read_bytes() == before
    assert json.loads((out / 'complete.json').read_text())['counts']['docs'] == 4
    retrieve_baseline(cache, tmp_path / 'reports', min_covered=1)
    retrieval = json.loads((tmp_path / 'reports/e5_tfidf_retrieval.json').read_text())
    assert retrieval['train_candidates'] == 2
    assert {n['lyrics_id'] for n in retrieval['queries'][0]['neighbors']} == {'a', 'b'}
    retrieve_embeddings(cache, models, tmp_path / 'reports')
    semantic = json.loads((tmp_path / 'reports/e5_embedding_retrieval.json').read_text())
    assert semantic['train_candidates'] == 2 and semantic['available_candidates'] == 2
    assert {n['lyrics_id'] for n in semantic['queries'][0]['neighbors']} == {'a', 'b'}


def test_parallel_writer_subruns(tmp_path):
    import json
    from sonora.nlp.semantic_parallel import train_parallel
    fixture(tmp_path)
    source = tmp_path / 'data/processed/lyrics/lyrics_full_v1/corpus/shard.parquet'
    rows = pq.read_table(source).to_pylist()
    rows[0]['lyrics_analysis'] = 'love home ' * 1000
    rows[1]['lyrics_analysis'] = 'love road ' * 1000
    rows[2]['lyrics_analysis'] = 'home road home'
    pq.write_table(pa.Table.from_pylist(rows), source)
    cache = prepare(tmp_path)
    fit_baseline(cache, min_df=1)
    out = tmp_path / 'artifacts/parallel-test'
    train_parallel(cache, out, tmp_path / 'runtime', workers=1)
    trained = json.loads((out / 'trained.json').read_text())
    assert trained['parallel'] and not trained['test_consumed']
    assert Path(trained['sgns']['path']).is_file()
    assert Path(trained['lda']['path']).is_file()
    assert len(list((out / 'sgns5').glob('sgns-window5/epoch-*.model'))) == 4
    assert len(list((out / 'sgns10').glob('sgns-window10/epoch-*.model'))) == 4
    assert not list((tmp_path / 'runtime/locks').glob('*.lock'))
