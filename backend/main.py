"""ASTRA-GUARD backend — FastAPI thin integration layer."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import camera, events, experiments, health, mission, protocol, sessions, status, voice

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="ASTRA-GUARD API",
        description=(
            "Thin REST integration layer over the existing ASTRA-GUARD "
            "mission system (EXP001 protocol). No duplicated decision logic."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):51[7-9][0-9]$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(mission.router, prefix="/api", tags=["mission"])
    app.include_router(events.router, prefix="/api", tags=["events"])
    app.include_router(status.router, prefix="/api", tags=["status"])
    app.include_router(voice.router, prefix="/api", tags=["voice"])
    app.include_router(camera.router, prefix="/api", tags=["camera"])
    app.include_router(experiments.router, prefix="/api", tags=["experiments"])
    app.include_router(sessions.router, prefix="/api", tags=["sessions"])
    app.include_router(protocol.router, tags=["protocol"])
    return app


app = create_app()
