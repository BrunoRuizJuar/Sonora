import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from sonora.nlp.semantics import config_hash, signature, words
from sonora.recommendation.catalog import Catalog, build_release
from sonora.recommendation.lyrics import recommend_lyrics
from sonora_api.main import create_app


@pytest.fixture
def release(tmp_path, monkeypatch):
    cache = tmp_path / 'cache'
    source = cache / 'representations'
    source.mkdir(parents=True)
    (cache / 'baseline').mkdir()
    vocab = cache / 'baseline/vocabulary.parquet'
    pq.write_table(pa.Table.from_pylist([dict(word='love', index=0, idf=1.), dict(word='road', index=1, idf=2.)]), vocab)
    from types import SimpleNamespace
    model_path = tmp_path / 'synthetic-model'
    model_path.write_text('synthetic fixture only')
    monkeypatch.setattr('sonora.nlp.semantic_models.load_model', lambda path: SimpleNamespace(wv={'love': np.array([1.,0.]), 'road': np.array([0.,1.])}))
    spec = {'vocabulary': signature(vocab), 'sgns': signature(model_path)}
    (source / 'config.json').write_text(json.dumps(spec))
    (source / 'complete.json').write_text(json.dumps({'space_id': config_hash(spec), 'counts': {'docs': 5, 'docs_train': 3, 'docs_validation': 1, 'docs_test': 1}}))
    rows = []
    for name, split, vector, artist in [('seed','validation',[1.,0.],'Author'),('near','train',[.8,.6],'Same'),('second','train',[.6,.8],'Same'),('other','test',[1.,0.],'Different'),('empty','train',[0.,0.],'Empty')]:
        rows.append(dict(lyrics_id=name, split=split, title=name, artist=artist, tag='pop', year=2000, embedding=vector, embedding_available=name!='empty', tfidf_indices=[0] if name in ('seed','other') else [1], tfidf_weights=[1.]))
    table = pa.Table.from_pylist(rows)
    table = table.set_column(table.schema.get_field_index('embedding'), 'embedding', pa.array([r['embedding'] for r in rows], type=pa.list_(pa.float32(),2)))
    pq.write_table(table, source/'part.parquet')
    root = tmp_path / 'release'
    build_release(source, root)
    return source, root


def test_release_matches_exact_and_filters(release):
    source, root = release
    c = Catalog(root)
    try:
        actual = c.recommend(identifier='seed', splits=('train',), top_k=2)
        reference = recommend_lyrics(source, 'seed', k=2)
        assert [r['id'] for r in actual['items']] == [r['lyrics_id'] for r in reference['neighbors']]
        assert [r['score'] for r in actual['items']] == pytest.approx([r['cosine'] for r in reference['neighbors']])
        assert [r['id'] for r in c.recommend(identifier='seed', max_per_artist=1)['items']] == ['other','near']
        assert [r['id'] for r in c.recommend(identifier='seed', strategy='tfidf')['items']] == ['other']
        assert c.recommend(identifier='seed', strategy='tfidf')['items'][0]['shared_terms'] == ['love']
        assert c.search('DIFF')[0]['id'] == 'other'
        assert c.search('" OR *') == []
        with pytest.raises(ValueError, match='disponible'):
            c.recommend(identifier='empty')
        with pytest.raises(KeyError):
            c.recommend(identifier='missing')
        # Resume uses committed shard without rebuilding.
        before = (root/'part/vectors.bin').stat().st_mtime_ns
        build_release(source, root)
        assert (root/'part/vectors.bin').stat().st_mtime_ns == before
    finally:
        c.close()


def test_frozen_query_and_oov(release):
    _, root = release
    c = Catalog(root)
    try:
        vector, idx, weight, coverage = c.query_text('LOVE love xyzzy')
        assert vector == pytest.approx([1,0])
        assert coverage == {'tokens': 3, 'covered_tokens': 2}
        assert c.recommend(text='love xyzzy', strategy='tfidf')['items'][0]['shared_terms'] == ['love']
        for text in ('', '123 !!!', 'xyzzy'):
            with pytest.raises(ValueError):
                c.recommend(text=text)
        assert words('Don’t ridin\'') == ["don't", 'ridin']
    finally:
        c.close()


def test_api_contract_and_readiness(release, tmp_path):
    _, root = release
    with TestClient(create_app(root)) as client:
        assert client.get('/api/v1/health/ready').status_code == 200
        assert client.get('/api/v1/catalog/stats').json()['rows'] == 5
        assert client.get('/api/v1/tracks/missing').status_code == 404
        assert client.get('/api/v1/tracks/search?q=near').json()['items'][0]['id'] == 'near'
        assert client.post('/api/v1/recommendations', json={'track_id':'seed','top_k':1}).json()['items'][0]['id'] == 'other'
        for body in ({}, {'text':' '}, {'track_id':'seed','text':'love'}, {'track_id':'seed','top_k':51}, {'track_id':'seed','candidate_splits':[]}, {'track_id':'seed','strategy':'lda'}):
            assert client.post('/api/v1/recommendations',json=body).status_code == 422
        assert client.post('/api/v1/recommendations',json={'track_id':'seed','mode':'mixed'}).status_code == 409
        assert client.post('/api/v1/recommendations',json={'track_id':'seed','exclude_known_covers':True}).status_code == 409
        assert client.post('/api/v1/recommendations',json={'track_id':'missing'}).status_code == 404
        assert client.get('/CLAUDE.md').status_code == 404
        assert 'player.js' in client.get('/').text
        assert 'app.js' in client.get('/letras.html').text
    with TestClient(create_app(tmp_path/'absent')) as client:
        assert client.get('/api/v1/health/live').status_code == 200
        assert client.get('/api/v1/health/ready').status_code == 503
        assert client.get('/api/v1/tracks/search?q=near').status_code == 503


def test_incomplete_release_refused(release):
    _, root = release
    (root/'part/vectors.bin').write_bytes(b'broken')
    with pytest.raises(ValueError, match='Incomplete'):
        Catalog(root)


def test_original_lyrics_identity_lines_and_api(release, tmp_path):
    from sonora.nlp.semantics import signature
    from sonora.recommendation.lyric_text import build_lyric_index, LyricTextStore
    _, root = release
    manifest = json.loads((root/'release.json').read_text('utf-8'))
    corpus = tmp_path/'originals'
    corpus.mkdir()
    original = '<script>not markup</script>\nFirst line\n\nLast line'
    pq.write_table(pa.Table.from_pylist([{'lyrics_id': key, 'lyrics_original': original if key=='seed' else key+'\nSecond verse'} for key in ('seed','near','second','other','empty')]), corpus/'part.parquet', row_group_size=2)
    index = tmp_path/'lyric-index'
    archived = signature(corpus/'part.parquet') | {'path': r'B:\SONORA\corpus\part.parquet'}
    build_lyric_index(corpus,index,manifest['space_id'],5,[archived])
    with TestClient(create_app(root, lyric_index=index)) as client:
        response = client.get('/api/v1/tracks/seed/lyrics')
        assert response.status_code == 200
        data = response.json()
        assert data['text'] == original
        assert data['lyrics_id'] == data['id'] == 'seed'
        assert data['title'] == 'seed'
        assert data['view'] == 'original'
        assert client.get('/api/v1/tracks/other/lyrics').json()['text'] == 'other\nSecond verse'
        assert client.get('/api/v1/tracks/missing/lyrics').status_code == 404
    with pytest.raises(ValueError, match='another catalog'):
        LyricTextStore(index,'wrong-space',5)
    with TestClient(create_app(root, lyric_index=tmp_path/'absent')) as client:
        assert client.get('/api/v1/tracks/seed/lyrics').status_code == 503
        assert client.get('/api/v1/health/ready').status_code == 200
    # Changed originals are refused, rather than showing a different lyric.
    with (corpus/'part.parquet').open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='changed'):
        LyricTextStore(index,manifest['space_id'],5)
    with pytest.raises(ValueError, match='frozen E5 inputs'):
        build_lyric_index(corpus,index,manifest['space_id'],5,[archived])
