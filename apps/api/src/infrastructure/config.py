"""
Application Configuration

Centralized configuration management using pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env variables
    )
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/hydroq_qc"
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return database URL compatible with SQLAlchemy (postgres -> postgresql)."""
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url
    database_echo: bool = Field(default=False)
    
    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=True)
    allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    )
    
    # Security
    jwt_secret_key: str = Field(default="dev-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=1440)  # 24 hours
    
    # File Storage
    data_dir: Path = Field(default=Path("./data"))
    upload_dir: Path = Field(default=Path("./data/uploads"))
    output_dir: Path = Field(default=Path("./data/outputs"))
    
    # ML Pipeline
    enable_autoencoder: bool = Field(default=False)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


class ProcessingConfig:
    """Processing configuration loaded from YAML."""
    
    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            # Look for config.yaml relative to this file
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        self._config: dict[str, Any] = {}
        self._load_config(config_path)
    
    def _load_config(self, config_path: Path) -> None:
        """Load config from YAML file."""
        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            # Use defaults if config file doesn't exist
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> dict[str, Any]:
        """Return default configuration."""
        return {
            "features": {
                "neighborhood": {"window_size": 5, "min_valid_neighbors": 3},
                "slope": {"method": "horn", "units": "degrees"},
                "roughness": {"window_size": 3},
                "laplacian": {"kernel_size": 3},
            },
            "anomaly_detection": {
                "isolation_forest": {
                    "enabled": True,
                    "n_estimators": 100,
                    "contamination": 0.1,
                    "max_samples": "auto",
                    "random_state": 42,
                    "n_jobs": -1,
                },
                "zscore": {
                    "enabled": True,
                    "threshold": 3.0,
                    "use_mad": True,
                    "mad_threshold": 3.5,
                },
                "autoencoder": {"enabled": False},
            },
            "scoring": {
                "weights": {
                    "isolation_forest": 0.5,
                    "zscore": 0.3,
                    "spatial_consistency": 0.2,
                },
                "confidence_thresholds": {"high": 0.8, "medium": 0.5},
            },
            "outputs": {
                "heatmap": {
                    "colormap": "RdYlGn_r",
                    "resolution_factor": 1.0,
                    "nodata_value": -9999,
                },
                "polygons": {
                    "anomaly_threshold": 0.6,
                    "min_area_pixels": 9,
                    "simplify_tolerance": 0.0001,
                },
            },
        }
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value by keys."""
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    @property
    def as_dict(self) -> dict[str, Any]:
        """Return full config as dictionary."""
        return self._config.copy()
    
    # Convenience properties
    @property
    def isolation_forest_config(self) -> dict[str, Any]:
        return self.get("anomaly_detection", "isolation_forest", default={})
    
    @property
    def zscore_config(self) -> dict[str, Any]:
        return self.get("anomaly_detection", "zscore", default={})
    
    @property
    def confidence_thresholds(self) -> dict[str, float]:
        return self.get("scoring", "confidence_thresholds", default={"high": 0.8, "medium": 0.5})
    
    @property
    def anomaly_threshold(self) -> float:
        return self.get("outputs", "polygons", "anomaly_threshold", default=0.6)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings


@lru_cache
def get_processing_config() -> ProcessingConfig:
    """Get cached processing config instance."""
    return ProcessingConfig()


# Singleton instances
settings = get_settings()
processing_config = get_processing_config()
