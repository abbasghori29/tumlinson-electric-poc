"""Shared dependencies for FastAPI routes"""
from functools import lru_cache
from app.core.config import Settings


@lru_cache()
def get_settings() -> Settings:
    """
    Dependency to get application settings
    Use @lru_cache() to create settings only once
    
    Usage in routes:
        @router.get("/example")
        def example(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()

