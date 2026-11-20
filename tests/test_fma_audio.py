import csv

from fastapi.testclient import TestClient

from sonora_api.main import create_app


def test_fma_metadata_join_search_and_mp3_ranges(tmp_path):
    metadata = tmp_path / 'fma_metadata/tracks.csv'
    metadata.parent.mkdir()
    with metadata.open('w', encoding='utf-8', newline='') as stream:
        csv.writer(stream).writerows([
            ['', 'artist', 'track', 'track'],
            ['', 'name', 'title', 'license'],
            ['track_id', '', '', ''],
            [2, 'José Álvarez', 'Río', 'Attribution 3.0'],
            [3, 'No audio', 'Pista ausente', ''],
            [4, '', 'Sol', ''],
        ])
    audio_folder = tmp_path / 'fma_medium/000'
    audio_folder.mkdir(parents=True)
    mp3 = b'ID3example'
    (audio_folder / '000002.mp3').write_bytes(mp3)
    (audio_folder / '000004.mp3').write_bytes(mp3)
    (audio_folder / '000005.mp3').write_bytes(mp3)

    app_options = dict(release=tmp_path / 'missing-release', fma_directory=tmp_path,
                       ratings_path=tmp_path / 'ratings.sqlite3')
    with TestClient(create_app(**app_options)) as client:
        response = client.get('/api/v1/fma/tracks', params={'q': 'rio jose'})
        assert response.status_code == 200
        assert response.json() == {'catalog_size': 2, 'items': [{
            'track_id': 2, 'title': 'Río', 'artist': 'José Álvarez',
            'license': 'Attribution 3.0', 'audio_url': '/api/v1/fma/tracks/2/audio',
        }]}
        url = response.json()['items'][0]['audio_url']
        assert client.get('/api/v1/fma/tracks', params={'q': '000002'}).json() == response.json()
        assert client.get('/api/v1/fma/tracks', params={'q': 'Sol'}).json()['items'][0]['artist'] == ''
        assert client.head(url).headers['content-type'] == 'audio/mpeg'
        assert client.get(url).content == mp3
        partial = client.get(url, headers={'Range': 'bytes=0-2'})
        assert partial.status_code == 206
        assert partial.content == b'ID3'
        assert client.get('/api/v1/fma/tracks/3/audio').status_code == 404
        assert client.get('/api/v1/fma/tracks/5/audio').status_code == 404
        related = client.get('/api/v1/fma/tracks/2/related').json()['items']
        assert [track['track_id'] for track in related] == [4]
        assert client.get('/api/v1/fma/tracks/3/related').status_code == 404
        assert client.get('/api/v1/fma/tracks/4/lyrics').status_code == 404
        assert client.get('/api/v1/health/ready').status_code == 503
        assert client.get('/api/v1/fma/tracks/2').json() == response.json()['items'][0]
        pair = {'query_id': 2, 'candidate_id': 4, 'rater_id': 'a' * 32}
        scores = {'emotion': 4, 'theme': 3, 'music_vibe': 4.5}
        assert client.post('/api/v1/audio/ratings', json=pair | scores).json() == {'rating': scores}

    with TestClient(create_app(**app_options)) as client:
        assert client.get('/api/v1/audio/ratings', params=pair).json() == {'rating': scores}
