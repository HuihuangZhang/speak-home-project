"""Tests for config loading."""


def test_settings_loads_from_env():
    from shared.config import settings
    # Env vars set in conftest.py
    assert settings.jwt_secret == "test-jwt-secret-32-chars-minimum!"
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"
    assert settings.session_pause_timeout_minutes == 5


def test_settings_has_livekit_config():
    from shared.config import settings
    assert settings.livekit_api_key == "test-api-key"
    assert settings.livekit_api_url == "https://livekit-api.example.com"
