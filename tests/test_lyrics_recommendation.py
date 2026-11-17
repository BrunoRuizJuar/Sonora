import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from sonora.recommendation.lyrics import recommend_lyrics
from sonora.storage.runs import config_hash


def test_frozen_space_retrieval_split_isolation_and_self_exclusion(tmp_path):
    spec = {'model': 'synthetic-space'}
    (tmp_path / 'config.json').write_text(json.dumps(spec))
    (tmp_path / 'complete.json').write_text(json.dumps({
        'space_id': config_hash(spec), 'counts': {'docs_train': 3, 'docs_validation': 1}}))
    rows = []
    for name, split, vector, available in [
        ('query', 'train', [1., 0.], True), ('near', 'train', [0.8, 0.6], True),
        ('empty', 'train', [0., 0.], False), ('heldout', 'validation', [1., 0.], True),
    ]:
        rows.append(dict(lyrics_id=name, split=split, title=name, artist='artist',
                         tag='pop', year=2000, embedding=vector, embedding_available=available))
    table = pa.Table.from_pylist(rows)
    table = table.set_column(table.schema.get_field_index('embedding'), 'embedding',
                             pa.array([r['embedding'] for r in rows], type=pa.list_(pa.float32(), 2)))
    pq.write_table(table, tmp_path / 'part.parquet')
    result = recommend_lyrics(tmp_path, 'query')
    assert [r['lyrics_id'] for r in result['neighbors']] == ['near']
    assert result['neighbors'][0]['cosine'] == pytest.approx(.8)
    result = recommend_lyrics(tmp_path, 'query', candidate_splits=('train', 'validation'))
    assert [r['lyrics_id'] for r in result['neighbors']] == ['heldout', 'near']
    with pytest.raises(ValueError, match='unavailable'):
        recommend_lyrics(tmp_path, 'empty')
    with pytest.raises(ValueError, match='Unknown'):
        recommend_lyrics(tmp_path, 'missing')
    (tmp_path / 'config.json').write_text('{}')
    with pytest.raises(ValueError, match='space'):
        recommend_lyrics(tmp_path, 'query')
