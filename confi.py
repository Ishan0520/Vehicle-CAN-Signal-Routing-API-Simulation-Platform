# core/config.py
# Central settings for the whole project.
# All other files import settings from here.

from pydantic_settings import BaseSettings
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    app_name: str = "Vehicle CAN Signal Routing Platform"
    app_version: str = "0.1.0"
    debug: bool = True

    can_interface: str = "virtual"
    can_channel: str = "vcan0"
    can_bitrate: int = 500_000

    dbc_file_path: Path = PROJECT_ROOT / "dbc" / "vehicle.dbc"
    feature_map_path: Path = PROJECT_ROOT / "mapping" / "feature_map.json"
    db_path: Path = PROJECT_ROOT / "db" / "signals.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
