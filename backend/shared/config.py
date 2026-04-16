from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load from the project-root .env, regardless of which directory
# the process is started from (backend/, project root, etc.)
_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ROOT_ENV), env_file_encoding="utf-8", extra="ignore")

    # LiveKit
    livekit_url: str = "wss://localhost"
    livekit_api_url: str = "https://localhost"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret"

    # AI Providers
    openai_api_key: str = ""
    deepgram_api_key: str = ""

    # Application
    jwt_secret: str = "changeme"
    jwt_expire_hours: int = 24
    database_url: str = "sqlite+aiosqlite:///./speakhome.db"
    session_pause_timeout_minutes: int = 5

    # When true, POST /sessions/{id}/force-expire skips auth (local/E2E only; never enable in prod)
    enable_test_utils: bool = False


settings = Settings()
