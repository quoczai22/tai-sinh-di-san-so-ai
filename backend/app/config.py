# pyrefly: ignore [missing-import]
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    DATABASE_URL: str = ""
    SUPABASE_DB_CONNECTION_STRING: str = ""

    model_config = SettingsConfigDict(
        env_file=(_BACKEND_DIR / ".env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_settings(self) -> "Settings":
        # Chuẩn hóa SUPABASE_URL nếu được cấu hình qua SUPABASE_DB_CONNECTION_STRING
        if not self.SUPABASE_URL and self.SUPABASE_DB_CONNECTION_STRING.startswith(("http://", "https://")):
            self.SUPABASE_URL = self.SUPABASE_DB_CONNECTION_STRING

        # Chuẩn hóa DATABASE_URL và SUPABASE_DB_CONNECTION_STRING cho kết nối PostgreSQL
        if not self.DATABASE_URL and self.SUPABASE_DB_CONNECTION_STRING.startswith(("postgres://", "postgresql://")):
            self.DATABASE_URL = self.SUPABASE_DB_CONNECTION_STRING
        elif self.DATABASE_URL and not self.SUPABASE_DB_CONNECTION_STRING:
            self.SUPABASE_DB_CONNECTION_STRING = self.DATABASE_URL

        return self

    @property
    def db_connection_string(self) -> str:
        return self.DATABASE_URL or self.SUPABASE_DB_CONNECTION_STRING


settings = Settings()

