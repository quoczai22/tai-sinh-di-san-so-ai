import urllib.parse
from pathlib import Path
# pyrefly: ignore [missing-import]
from pydantic import model_validator
# pyrefly: ignore [missing-import]
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

    # Optional individual DB variables
    DB_CONNECTION: str = "postgresql"
    DB_HOST: str = ""
    DB_PORT: int | str = ""
    DB_DATABASE: str = ""
    DB_USERNAME: str = ""
    DB_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=(_BACKEND_DIR / ".env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_settings(self) -> "Settings":
        # Tự động tạo DATABASE_URL nếu dùng các biến rời rạc DB_HOST, DB_USERNAME,...
        if not self.DATABASE_URL and self.DB_HOST and self.DB_USERNAME:
            driver = "postgresql" if self.DB_CONNECTION in ("pgsql", "postgres", "postgresql") else self.DB_CONNECTION
            port_str = f":{self.DB_PORT}" if self.DB_PORT else ""
            db_name = self.DB_DATABASE or "postgres"
            encoded_pwd = urllib.parse.quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
            auth = f"{self.DB_USERNAME}:{encoded_pwd}" if encoded_pwd else self.DB_USERNAME
            self.DATABASE_URL = f"{driver}://{auth}@{self.DB_HOST}{port_str}/{db_name}"

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

