"""Settings, read from .env at the repo root."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str = ""

    atelier_model: str = "claude-opus-5"
    atelier_effort: str = "high"
    atelier_region: str = "US"
    # Region is a preference, not a filter: with this on, retailers that ship
    # worldwide are offered alongside local ones, labelled as overseas.
    atelier_include_international: bool = True
    atelier_web_search: bool = True
    atelier_data_dir: Path = REPO_ROOT / "data"

    pinterest_client_id: str = ""
    pinterest_client_secret: str = ""
    pinterest_redirect_uri: str = "http://localhost:8787/api/pinterest/callback"

    @property
    def data_dir(self) -> Path:
        p = self.atelier_data_dir
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def image_dir(self) -> Path:
        p = self.data_dir / "images"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        return self.data_dir / "atelier.db"

    @property
    def pinterest_configured(self) -> bool:
        return bool(self.pinterest_client_id and self.pinterest_client_secret)

    @property
    def claude_configured(self) -> bool:
        # An empty env var does not mean no credentials - the SDK also reads
        # ANTHROPIC_AUTH_TOKEN and `ant auth login` profiles. Treat an explicit
        # key as definitive and let the SDK resolve the rest at call time.
        import os

        return bool(
            self.anthropic_api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or (Path.home() / ".config" / "anthropic").exists()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
