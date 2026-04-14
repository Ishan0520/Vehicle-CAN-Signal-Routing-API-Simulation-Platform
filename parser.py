# dbc/parser.py
# Reads the vehicle.dbc file and can encode/decode CAN signals.
# This is the ONLY file that uses cantools directly.

import cantools
import cantools.database
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DBCParser:
    def __init__(self, dbc_path):
        self._path = Path(dbc_path)
        self._db = self._load()

    def _load(self):
        if not self._path.exists():
            raise FileNotFoundError(f"DBC file not found: {self._path}")
        db = cantools.database.load_file(str(self._path))
        logger.info(f"DBC loaded: {self._path.name} | {len(db.messages)} messages")
        return db

    def get_message_by_name(self, message_name: str):
        try:
            return self._db.get_message_by_name(message_name)
        except KeyError:
            available = [m.name for m in self._db.messages]
            raise KeyError(f"Message '{message_name}' not found. Available: {available}")

    def get_message_by_id(self, message_id: int):
        try:
            return self._db.get_message_by_frame_id(message_id)
        except KeyError:
            raise KeyError(f"Message ID 0x{message_id:03X} not in DBC.")

    def list_messages(self) -> list[dict]:
        result = []
        for msg in self._db.messages:
            result.append({
                "name": msg.name,
                "id": msg.frame_id,
                "id_hex": f"0x{msg.frame_id:03X}",
                "signals": [{"name": s.name, "scale": s.scale, "offset": s.offset, "unit": s.unit}
                            for s in msg.signals],
            })
        return result

    def encode_signal(self, message_name: str, signal_name: str, value: float) -> tuple[int, bytes]:
        msg = self.get_message_by_name(message_name)
        data = msg.encode({signal_name: value}, padding=True, strict=False)
        logger.debug(f"Encoded | msg={message_name} signal={signal_name} value={value} → {data.hex()}")
        return msg.frame_id, data

    def decode_message(self, message_id: int, data: bytes) -> Optional[dict]:
        try:
            msg = self.get_message_by_id(message_id)
            return msg.decode(data, decode_choices=False)
        except KeyError:
            return None