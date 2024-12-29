from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings."""
    mongodb_uri: str = "mongodb+srv://hidevscommunity:FzrvrarB8zcQsubp@cluster0.ajsozyu.mongodb.net/hidevs_foundations?retryWrites=true&w=majority&tls=true"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings() 