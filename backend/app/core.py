from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./data/app.db'
    storage_root: Path = Path('./storage')
    max_upload_mb: int = 100
    cors_origins: str = 'http://localhost:5173'
    api_prefix: str = '/api'

settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)

CPU_COUNT = os.cpu_count() or 1
