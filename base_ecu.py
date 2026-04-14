# ecu_sim/base_ecu.py
# The parent class all ECUs inherit from.
# Handles: connecting to bus, running listener thread, decoding frames.
# Each specific ECU only needs to say WHAT to do when it gets a message.

import threading
import logging
from abc import ABC, abstractmethod
from typing import Optional
import can

from can_sim.bus import CANBus
from dbc.parser import DBCParser
from core.config import settings

logger = logging.getLogger(__name__)


class BaseECU(ABC):
    LISTEN_IDS: set[int] = set()

    def __init__(self, name: str):
        self.name = name
        self.state: dict = {}
        self._bus = CANBus()
        self._parser = DBCParser(settings.dbc_file_path)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._bus.connect()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"{self.name}-thread", daemon=True)
        self._thread.start()
        logger.info(f"[{self.name}] started — listening for IDs: {[hex(i) for i in self.LISTEN_IDS]}")

    def stop(self) -> None:
        logger.info(f"[{self.name}] stopping...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._bus.disconnect()
        logger.info(f"[{self.name}] stopped.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            msg: Optional[can.Message] = self._bus.receive_one(timeout=0.1)
            if msg is None:
                continue
            if msg.arbitration_id not in self.LISTEN_IDS:
                continue
            decoded = self._parser.decode_message(msg.arbitration_id, bytes(msg.data))
            if decoded is None:
                continue
            self.on_message(message_id=msg.arbitration_id, signals=decoded, raw=bytes(msg.data))

    @abstractmethod
    def on_message(self, message_id: int, signals: dict, raw: bytes) -> None:
        ...

    def get_state(self) -> dict:
        return dict(self.state)