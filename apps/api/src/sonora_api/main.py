"""Same-origin web and frozen E5 text catalog."""
from contextlib import asynccontextmanager
import csv
import logging
import os
import sqlite3
from pathlib import Path
import threading
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sonora.recommendation.catalog import Catalog
from sonora.recommendation.lyric_text import LyricTextStore

ROOT = Path(__file__).resolve().parents[4]


from sonora_api.fma_audio import AudioCatalog
from sonora_api.ratings import read_rating, save_rating
from sonora_api.schemas.recommendations import AudioRating, RaterId, RecommendationRating, RecommendationRequest, SongRating


def create_app(release=None, lyric_index=None, ratings_path=None, fma_directory=None):
    ratings_path = Path(ratings_path or os.environ.get(
        'SONORA_RATINGS_DB', ROOT / 'runtime/feedback/ratings.sqlite3'
    ))
    fma_directory = Path(fma_directory or os.environ.get(
        'SONORA_FMA_DIRECTORY', ROOT / 'data/raw/fma'
    ))
    @asynccontextmanager
    async def lifespan(app):
        start = time.perf_counter()
        app.state.catalog = None
        app.state.error = None
        app.state.lyrics = None
        app.state.lock = threading.Lock()
        try:
            app.state.catalog = Catalog(release or os.environ.get('SONORA_TEXT_RELEASE', str(ROOT / 'artifacts/releases/lyrics-serving-v1')))
        except (OSError, ValueError, KeyError) as exc:
            app.state.error = f'Release textual no disponible: {type(exc).__name__}'
        if app.state.catalog:
            try:
                app.state.lyrics = LyricTextStore(lyric_index or os.environ.get('SONORA_LYRIC_INDEX', str(ROOT / 'artifacts/releases/lyrics-original-v1')), app.state.catalog.manifest['space_id'], app.state.catalog.manifest['rows'])
            except (OSError, ValueError, KeyError, sqlite3.Error):
                pass  # Recommendations remain available when original text is not installed.
        app.state.startup_seconds = time.perf_counter() - start
        app.state.fma = None
        metadata = fma_directory / 'fma_metadata/tracks.csv'
        if metadata.is_file():
            try:
                links = Path(os.environ.get('SONORA_AUDIO_LYRICS_LINKS',
                    ROOT / 'data/processed/demo/lyrics_full_v1/demo_links.csv'))
                app.state.fma = AudioCatalog(metadata, fma_directory / 'fma_medium', links)
            except (OSError, ValueError, KeyError, IndexError, csv.Error) as exc:
                logging.getLogger(__name__).warning('Catálogo FMA no disponible: %s', exc)
        app.state.recording_by_lyric = {}
        if app.state.fma:
            for track_id, lyric_id in sorted(app.state.fma.lyrics_ids.items()):
                if track_id in app.state.fma.recordings:
                    app.state.recording_by_lyric.setdefault(lyric_id, track_id)
        yield
        if app.state.catalog:
            app.state.catalog.close()
        if app.state.lyrics:
            app.state.lyrics.close()

    app = FastAPI(title='SONORA API', version='0.2.0', lifespan=lifespan)

    def catalog():
        service = getattr(app.state, 'catalog', None)
        if service is None:
            raise HTTPException(503, getattr(app.state, 'error', None) or 'Release textual no disponible')
        return service

    @app.get('/api/v1/health/live')
    def live():
        return {'status': 'alive', 'version': '0.2.0'}

    @app.get('/api/v1/health/ready')
    def ready():
        service = getattr(app.state, 'catalog', None)
        if service is None:
            return JSONResponse(status_code=503, content={'status': 'not_ready', 'reason': getattr(app.state, 'error', None)})
        return {'status': 'ready', 'space_id': service.manifest['space_id'], 'startup_seconds': app.state.startup_seconds}

    @app.get('/api/v1/catalog/stats')
    def stats():
        service = catalog()
        return {k: service.manifest[k] for k in ('version', 'release_id', 'space_id', 'rows', 'dimensions')} | {'capabilities': {'lyrics': True, 'audio': False, 'mixed': False, 'strategies': ['sgns', 'tfidf']}, 'id_policy': 'track_id = canonical lyrics_id; no verified recording mapping', 'scope': 'all splits, exploratory browsing; not held-out relevance evaluation', 'language': 'English model; no translation', 'covers': 'unverified', 'startup_seconds': app.state.startup_seconds}

    def fma_catalog():
        service = getattr(app.state, 'fma', None)
        if service is None:
            raise HTTPException(503, 'El catálogo local de audio FMA no está disponible.')
        return service

    @app.get('/api/v1/fma/tracks')
    def fma_search(q: str = Query(default='', max_length=200),
                   limit: int = Query(default=12, ge=1, le=50)):
        service = fma_catalog()
        return {'items': service.search(q, limit), 'catalog_size': len(service.recordings)}

    @app.get('/api/v1/fma/tracks/{track_id}/related')
    def related_audio(track_id: int):
        try:
            return {'items': fma_catalog().related(track_id)}
        except KeyError:
            raise HTTPException(404, 'Pista desconocida.')

    @app.get('/api/v1/fma/tracks/{track_id}')
    def audio_detail(track_id: int):
        recording = fma_catalog().recordings.get(track_id)
        if recording is None:
            raise HTTPException(404, 'Pista desconocida.')
        return recording.public()

    @app.get('/api/v1/fma/tracks/{track_id}/lyrics')
    def audio_lyrics(track_id: int):
        identifier = fma_catalog().lyrics_ids.get(track_id)
        if identifier is None:
            raise HTTPException(404, 'Esta pista no tiene letra en SONORA.')
        return lyrics(identifier)

    @app.api_route('/api/v1/fma/tracks/{track_id}/audio', methods=['GET', 'HEAD'])
    def fma_audio(track_id: int):
        service = fma_catalog()
        recording = service.recordings.get(track_id)
        if recording is None:
            raise HTTPException(404, 'Audio FMA no disponible.')
        path = recording.path.resolve()
        if not path.is_relative_to(service.root) or not path.is_file():
            raise HTTPException(404, 'Audio FMA no disponible.')
        return FileResponse(path, media_type='audio/mpeg')

    @app.get('/api/v1/tracks/search')
    def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=50)):
        service = catalog()
        with app.state.lock:
            return {'items': service.search(q, limit), 'space_id': service.manifest['space_id']}

    @app.get('/api/v1/tracks/{track_id}')
    def detail(track_id: str):
        service = catalog()
        with app.state.lock:
            try:
                _, row = service.locate(track_id)
                return service.public(row) | {'space_id': service.manifest['space_id']}
            except KeyError:
                raise HTTPException(404, 'Letra desconocida')

    @app.get('/api/v1/tracks/{track_id}/lyrics')
    def lyrics(track_id: str):
        service = catalog()
        with app.state.lock:
            try:
                _, row = service.locate(track_id)
                if app.state.lyrics is None:
                    raise HTTPException(503, 'Las letras originales aún no están disponibles')
                return service.public(row) | app.state.lyrics.get(track_id)
            except KeyError:
                raise HTTPException(404, 'Letra desconocida')
            except (OSError, ValueError):
                raise HTTPException(409, 'No se pudo recuperar la letra original de esta canción')

    def song_id(identifier):
        if identifier.isascii() and identifier.isdigit():
            audio = app.state.fma
            identifier = audio.lyrics_ids.get(int(identifier)) if audio else None
            if not identifier:
                raise HTTPException(404, 'Esta canción no tiene letra disponible.')
        return identifier

    def song_public(lyric):
        identifier = lyric['lyrics_id']
        recording_id = app.state.recording_by_lyric.get(identifier)
        recording = app.state.fma.recordings[recording_id].public() if recording_id is not None else {}
        return recording | {
            'track_id': identifier, 'id': identifier, 'lyrics_id': identifier,
            'title': lyric['title'], 'artist': lyric['artist'], 'split': lyric['split'],
            'recording_id': recording_id, 'audio_url': recording.get('audio_url'),
        }

    def songs_with_lyrics(items, limit):
        songs = []
        for item in items:
            try:
                songs.append(song_public(lyrics(item['lyrics_id'])))
            except HTTPException as error:
                if error.status_code == 503:
                    raise
                continue
            if len(songs) == limit:
                break
        return songs

    @app.get('/api/v1/songs')
    def songs_search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=12, ge=1, le=20)):
        service = catalog()
        with app.state.lock:
            items = service.search(q, limit * 2)
        query = q.strip().casefold()
        items.sort(key=lambda item: (
            query not in (item['title'].casefold(), f"{item['title']} {item['artist']}".casefold()),
            item['title'].casefold(),
        ))
        return {'items': songs_with_lyrics(items, limit)}

    @app.get('/api/v1/songs/{identifier}')
    def song_detail(identifier: str):
        return song_public(lyrics(song_id(identifier)))

    @app.get('/api/v1/songs/{identifier}/lyrics')
    def song_lyrics(identifier: str):
        return lyrics(song_id(identifier))

    @app.get('/api/v1/songs/{identifier}/related')
    def song_related(identifier: str):
        origin = song_detail(identifier)
        canonical = origin['track_id']
        if origin['recording_id'] is not None:
            audio = fma_catalog()
            eligible = set(app.state.recording_by_lyric.values())
            items = [{'lyrics_id': audio.lyrics_ids[item['track_id']]} for item in
                     audio.related(origin['recording_id'], eligible, limit=40)]
            return {'items': songs_with_lyrics(items, 20)}
        with app.state.lock:
            try:
                items = catalog().recommend(identifier=canonical, top_k=40)['items']
            except ValueError:
                return {'items': []}
        return {'items': songs_with_lyrics(items, 20)}

    @app.post('/api/v1/recommendations')
    def recommend(request: RecommendationRequest, require_lyrics: bool = False):
        service = catalog()
        if request.mode != 'lyrics' or request.exclude_known_covers:
            raise HTTPException(409, 'Audio, Mixto y exclusiÃ³n de covers no estÃ¡n disponibles')
        with app.state.lock:
            try:
                result = service.recommend(identifier=request.track_id, text=request.text, strategy=request.strategy, top_k=min(50, request.top_k * 2) if require_lyrics else request.top_k, splits=tuple(request.candidate_splits), max_per_artist=request.max_per_artist)
            except KeyError:
                raise HTTPException(404, 'Letra desconocida')
            except ValueError as exc:
                raise HTTPException(422, str(exc))
        if require_lyrics:
            valid = {song['track_id'] for song in songs_with_lyrics(result['items'], request.top_k)}
            result['items'] = [item for item in result['items'] if item['lyrics_id'] in valid]
            result['total_returned'] = len(result['items'])
        return result

    @app.get('/api/v1/recommendations/ratings')
    def get_rating(rater_id: RaterId, release_id: str = Query(min_length=1, max_length=100),
                   query_id: str = Query(min_length=1, max_length=100),
                   candidate_id: str = Query(min_length=1, max_length=100)):
        if release_id != catalog().manifest['release_id']:
            raise HTTPException(409, 'Actualiza la lista de recomendaciones.')
        return rating_response(release_id, query_id, candidate_id, rater_id)

    def rating_response(release_id, query_id, candidate_id, rater_id):
        try:
            rating = read_rating(ratings_path, (release_id, query_id, candidate_id, rater_id))
        except (OSError, sqlite3.Error):
            raise HTTPException(503, 'No se pudieron consultar las calificaciones.')
        return JSONResponse({'rating': rating}, headers={'Cache-Control': 'no-store'})

    @app.post('/api/v1/recommendations/ratings')
    def rate(rating: RecommendationRating):
        service = catalog()
        if rating.release_id != service.manifest['release_id']:
            raise HTTPException(409, 'Actualiza la lista de recomendaciones.')
        if rating.query_id == rating.candidate_id:
            raise HTTPException(422, 'Elige dos canciones distintas.')
        with app.state.lock:
            try:
                for identifier in (rating.query_id, rating.candidate_id):
                    _, row = service.locate(identifier)
                    if not row['available']:
                        raise KeyError(identifier)
            except KeyError:
                raise HTTPException(404, 'Letra desconocida o no disponible.')
        return persist_rating(rating.model_dump())

    def persist_rating(values):
        try:
            save_rating(ratings_path, values)
        except (OSError, sqlite3.Error):
            raise HTTPException(503, 'No se pudo guardar la calificación. Inténtalo de nuevo.')
        return {'rating': {axis: values[axis] for axis in ('theme', 'emotion', 'music_vibe')}}

    audio_release = 'fma-medium-genre-v1'

    @app.get('/api/v1/audio/ratings')
    def get_audio_rating(rater_id: RaterId, query_id: int = Query(gt=0), candidate_id: int = Query(gt=0)):
        return rating_response(audio_release, str(query_id), str(candidate_id), rater_id)

    @app.post('/api/v1/audio/ratings')
    def rate_audio(rating: AudioRating):
        if rating.query_id == rating.candidate_id:
            raise HTTPException(422, 'Elige dos canciones distintas.')
        audio = fma_catalog()
        if rating.query_id not in audio.recordings or rating.candidate_id not in audio.recordings:
            raise HTTPException(404, 'Pista desconocida.')
        rank = next((index for index, item in enumerate(audio.related(rating.query_id), 1)
                     if item['track_id'] == rating.candidate_id), 0)
        return persist_rating(rating.model_dump() | {
            'release_id': audio_release, 'strategy': 'genre_artist', 'rank': rank,
            'query_id': str(rating.query_id), 'candidate_id': str(rating.candidate_id),
        })

    def song_pair(query_id, candidate_id):
        first, second = song_detail(query_id), song_detail(candidate_id)
        if first['track_id'] == second['track_id']:
            raise HTTPException(422, 'Elige dos canciones distintas.')
        if first['recording_id'] is not None and second['recording_id'] is not None:
            return audio_release, str(first['recording_id']), str(second['recording_id'])
        return catalog().manifest['release_id'], first['track_id'], second['track_id']

    @app.get('/api/v1/song-ratings')
    def get_song_rating(query_id: str, candidate_id: str, rater_id: RaterId):
        return rating_response(*song_pair(query_id, candidate_id), rater_id)

    @app.post('/api/v1/song-ratings')
    def rate_song(rating: SongRating):
        release, query_id, candidate_id = song_pair(rating.query_id, rating.candidate_id)
        return persist_rating(rating.model_dump() | {
            'release_id': release, 'query_id': query_id, 'candidate_id': candidate_id,
            'strategy': 'genre_artist' if release == audio_release else 'sgns',
        })

    @app.get('/index.html', include_in_schema=False)
    @app.get('/')
    def portal():
        return FileResponse(ROOT / 'apps/web/public/letras.html')

    app.mount('/', StaticFiles(directory=ROOT / 'apps/web/public', html=True), name='web')
    return app


app = create_app()
