import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# Optional New Relic import (only for production)
try:
    import newrelic.agent
    NEW_RELIC_AVAILABLE = True
except ImportError:
    NEW_RELIC_AVAILABLE = False

# load_dotenv()  # Explicitly load the .env file
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


class Settings(BaseSettings):
    """
    Centralized configuration management using Pydantic
    """

    # Google Drive Configuration (API Key for public folders)
    GOOGLE_DRIVE_API_KEY: Optional[str] = None

    # Directories
    TEMP_DIR: str = "/tmp/audio_processing"
    DOWNLOAD_DIR: str = "./audio_downloads"
    OUTPUT_DIR: str = "./transcriptions"

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    PORT: int = 8000

    # AI/ML Service Configuration
    GEMINI_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT: int = 600

    # Audio Processing Configuration
    MAX_AUDIO_SIZE_MB: int = 200
    MAX_AUDIO_DURATION_SECONDS: int = 7200  # 2 hours
    SUPPORTED_AUDIO_FORMATS: str = "mp3,wav,m4a,aac,ogg,flac,opus"
    MAX_CHUNK_SIZE_MB: int = 20  # Max chunk size for processing

    # Processing Configuration
    CLEANUP_TEMP_FILES: bool = True
    MAX_CONCURRENT_PROCESSING: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    NODE_ENV: str = "development"

    # Optional Kafka Configuration (if you want to keep it for future use)
    KAFKA_BROKER: Optional[str] = None
    KAFKA_ENABLED: bool = False

    def get_supported_audio_formats(self) -> list:
        """Get list of supported audio formats"""
        return [fmt.strip().lower() for fmt in self.SUPPORTED_AUDIO_FORMATS.split(",")]

    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.NODE_ENV.lower() == "development"

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.NODE_ENV.lower() == "production"

    def validate_required_fields(self):
        """Validate that required fields are set"""
        if not self.GEMINI_KEY:
            raise ValueError(
                "GEMINI_KEY is required! Please set it in your .env file or environment variables.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )



class ProductionSettings(Settings):
    # Production-only fields
    NEW_RELIC_LICENSE_KEY: Optional[str] = None
    NEW_RELIC_APP_NAME: Optional[str] = None

    # Model configuration for environment variable loading
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_settings():
    """Factory function to return appropriate settings class"""
    environment = os.getenv("NODE_ENV", "development").lower()

    if environment == "production":
        return ProductionSettings()
    else:
        return Settings()


# Instantiate settings
settings = get_settings()
