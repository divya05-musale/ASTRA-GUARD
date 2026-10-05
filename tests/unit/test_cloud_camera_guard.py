from backend.core.config import Settings


def test_cloud_mode_forces_camera_disabled(monkeypatch):
    monkeypatch.setenv("ASTRA_GUARD_MODE", "cloud")
    monkeypatch.setenv("ASTRA_GUARD_ENABLE_LIVE_PERCEPTION", "true")

    settings = Settings()

    assert settings.MODE == "cloud"
    assert settings.ENABLE_LIVE_PROCESSOR is False
    assert settings.is_cloud_mode() is True


def test_cors_origins_are_parsed_from_environment(monkeypatch):
    monkeypatch.setenv("ASTRA_GUARD_CORS_ORIGINS", "https://demo.vercel.app, http://localhost:5173")

    settings = Settings()

    assert settings.BACKEND_CORS_ORIGINS == [
        "https://demo.vercel.app",
        "http://localhost:5173",
    ]
