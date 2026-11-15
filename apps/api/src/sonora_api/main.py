"""Minimal process health; recommendation services are not implemented yet."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="SONORA API", version="0.1.0")


@app.get("/api/v1/health/live", tags=["health"])
def live() -> dict:
    return {"status": "alive", "stage": "scaffold", "version": "0.1.0"}


@app.get("/api/v1/health/ready", tags=["health"], responses={503: {"description": "Not ready"}})
def ready() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "reason": "Catalog, models and service adapters are not integrated yet.",
        },
    )
