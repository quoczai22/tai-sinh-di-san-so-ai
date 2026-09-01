# pyrefly: ignore [missing-import]
from supabase import Client, create_client

from app.config import settings

_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Khởi tạo Supabase client
    """
    global _client
    if _client is not None:
        return _client

    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL chưa được cấu hình")

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY chưa được cấu hình")

    _client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
    return _client
