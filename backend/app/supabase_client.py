from typing import Optional
from supabase import Client, create_client
from app.config import settings


_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Get or initialize the Supabase client using environment configurations.
    """
    global _client
    if _client is not None:
        return _client

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        return _client

    return None
