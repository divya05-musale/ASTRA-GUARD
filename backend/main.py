"""ASTRA-GUARD backend — FastAPI thin integration layer."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import camera, events, experiments, health, mission, protocol, sessions, status, voice
from backend.core.config import get_settings
from backend.services.camera_service import stop_camera_service


settings = get_settings()
ALLOWED_ORIGINS = settings.BACKEND_CORS_ORIGINS or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    allowed_origins = list(ALLOWED_ORIGINS)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        stop_camera_service()

    app = FastAPI(
        title="ASTRA-GUARD API",
        description=(
            "Thin REST integration layer over the existing ASTRA-GUARD "
            "mission system (EXP001 protocol). No duplicated decision logic."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^(https?://)?(localhost|127\.0\.0\.1|.*\.vercel\.app)(:\d+)?$",
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
