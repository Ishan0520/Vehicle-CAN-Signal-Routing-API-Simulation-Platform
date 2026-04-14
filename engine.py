# mapping/engine.py
# Reads feature_map.json and answers:
# "Given feature name + value, which signal do I set and to what?"

import json
import logging
from pathlib import Path
from typing import Optional

from models.feature import MappingEntry
from core.config import settings

logger = logging.getLogger(__name__)


class MappingEngine:
    def __init__(self, map_path=None):
        self._path = Path(map_path or settings.feature_map_path)
        self._map: dict[str, MappingEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Feature map not found: {self._path}")

        with open(self._path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        count = 0
        for feature_name, entry_data in raw.items():
            if feature_name.startswith("_"):
                continue
            self._map[feature_name] = MappingEntry(
                feature_name=feature_name,
                description=entry_data.get("description", ""),
                message_name=entry_data["message_name"],
                signal_name=entry_data["signal_name"],
                value_map=entry_data.get("value_map", {}),
                default_value=float(entry_data.get("default_value", 0)),
                value_description=entry_data.get("value_description", ""),
            )
            count += 1

        logger.info(f"MappingEngine loaded {count} features from {self._path.name}")

    def resolve(self, feature_name: str, requested_value: Optional[float] = None) -> tuple[MappingEntry, float]:
        entry = self.get_entry(feature_name)

        if entry.value_map and requested_value is not None:
            key = str(int(requested_value))
            if key not in entry.value_map:
                raise ValueError(
                    f"Feature '{feature_name}': value {requested_value} is not valid.\n"
                    f"Allowed values: {list(entry.value_map.keys())}\n"
                    f"Hint: {entry.value_description}"
                )
            final_value = float(entry.value_map[key])
        elif requested_value is not None:
            final_value = float(requested_value)
        else:
            final_value = entry.default_value

        logger.debug(f"Resolved: {feature_name} → {entry.message_name}/{entry.signal_name} = {final_value}")
        return entry, final_value

    def get_entry(self, feature_name: str) -> MappingEntry:
        if feature_name not in self._map:
            available = sorted(self._map.keys())
            raise KeyError(f"Feature '{feature_name}' not found.\nAvailable: {available}")
        return self._map[feature_name]

    def list_features(self) -> list[dict]:
        return [
            {
                "feature_name": name,
                "description": e.description,
                "message_name": e.message_name,
                "signal_name": e.signal_name,
                "default_value": e.default_value,
                "value_description": e.value_description,
            }
            for name, e in sorted(self._map.items())
        ]

    def feature_exists(self, feature_name: str) -> bool:
        return feature_name in self._map

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        return f"MappingEngine(features={len(self._map)})"