from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
BASE_DIR = BACKEND_DIR

class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True

    # GMGN Client
    GMGN_BASE_URL: str = "https://gmgn.ai"
    GMGN_API_KEY: Optional[str] = None
    COLLECTOR_TIMEOUT: int = 15
    COLLECTOR_RETRY_COUNT: int = 3

    # Storage & Cache
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'storage' / 'ai_trader.db'}"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Chains
    DEFAULT_CHAIN: str = "sol"

    # Directory Paths
    BASE_PATH: Path = BASE_DIR
    DATA_PATH: Path = BASE_DIR / "data"
    DATASETS_PATH: Path = BASE_DIR / "data" / "datasets"
    RAW_DATA_PATH: Path = BASE_DIR / "data" / "datasets" / "raw"
    PROCESSED_DATA_PATH: Path = BASE_DIR / "data" / "datasets" / "processed"
    TRAINING_DATA_PATH: Path = BASE_DIR / "data" / "datasets" / "training"
    STORAGE_PATH: Path = BASE_DIR / "data" / "storage"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        """Ensure all storage and dataset directories exist."""
        for path in [
            self.DATA_PATH,
            self.DATASETS_PATH,
            self.RAW_DATA_PATH,
            self.PROCESSED_DATA_PATH,
            self.TRAINING_DATA_PATH,
            self.STORAGE_PATH,
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
