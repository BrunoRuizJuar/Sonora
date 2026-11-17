"""Same-origin web and frozen E5 text catalog."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sonora.recommendation.catalog import Catalog

ROOT = Path(__file__).resolve().parents[4]


from sonora_api.schemas.recommendations import RecommendationRequest


def create_app(release=None):
    @asynccontextmanager
    async def lifespan(app):
        start = time.perf_counter()
        app.state.catalog = None
        app.state.error = None
        app.state.lock = threading.Lock()
        try:
            app.state.catalog = Catalog(release or os.environ.get('SONORA_TEXT_RELEASE', str(ROOT / 'artifacts/releases/lyrics-serving-v1')))
        except (OSError, ValueError, KeyError) as exc:
            app.state.error = f'Release textual no disponible: {type(exc).__name__}'
        app.state.startup_seconds = time.perf_counter() - start
        yield
        if app.state.catalog:
            app.state.catalog.close()

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
        return {k: service.manifest[k] for k in ('version', 'space_id', 'rows', 'dimensions')} | {'capabilities': {'lyrics': True, 'audio': False, 'mixed': False, 'strategies': ['sgns', 'tfidf']}, 'id_policy': 'track_id = canonical lyrics_id; no verified recording mapping', 'scope': 'all splits, exploratory browsing; not held-out relevance evaluation', 'language': 'English model; no translation', 'covers': 'unverified', 'startup_seconds': app.state.startup_seconds}

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

    @app.post('/api/v1/recommendations')
    def recommend(request: RecommendationRequest):
        service = catalog()
        if request.mode != 'lyrics' or request.exclude_known_covers:
            raise HTTPException(409, 'Audio, Mixto y exclusiÃ³n de covers no estÃ¡n disponibles')
        with app.state.lock:
            try:
                return service.recommend(identifier=request.track_id, text=request.text, strategy=request.strategy, top_k=request.top_k, splits=tuple(request.candidate_splits), max_per_artist=request.max_per_artist)
            except KeyError:
                raise HTTPException(404, 'Letra desconocida')
            except ValueError as exc:
                raise HTTPException(422, str(exc))

    app.mount('/', StaticFiles(directory=ROOT / 'apps/web/public', html=True), name='web')
    return app


app = create_app()
