# can_sim/bus.py
# Creates a virtual CAN bus. Sends and receives CAN frames.
# No real hardware needed — uses python-can virtual interface.

import can
import logging
import threading
from typing import Optional, Callable
from core.config import settings

logger = logging.getLogger(__name__)


class CANBus:
    def __init__(self, interface=None, channel=None, bitrate=None):
        self._interface = interface or settings.can_interface
        self._channel = channel or settings.can_channel
        self._bitrate = bitrate or settings.can_bitrate
        self._bus: Optional[can.BusABC] = None
        self._is_connected: bool = False

    def connect(self) -> None:
        if self._is_connected:
            return
        try:
            self._bus = can.interface.Bus(
                interface=self._interface,
                channel=self._channel,
                bitrate=self._bitrate,
            )
            self._is_connected = True
            logger.info(f"CAN bus connected | interface={self._interface} channel={self._channel}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to CAN bus: {e}") from e

    def disconnect(self) -> None:
        if self._bus and self._is_connected:
            self._bus.shutdown()
            self._is_connected = False
            logger.info("CAN bus disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def send(self, frame_id: int, data: bytes, is_extended_id: bool = False) -> None:
        if not self._is_connected or self._bus is None:
            raise RuntimeError("CAN bus is not connected.")
        padded = data.ljust(8, b'\x00')[:8]
        message = can.Message(arbitration_id=frame_id, data=padded, is_extended_id=is_extended_id)
        try:
            self._bus.send(message)
            logger.debug(f"CAN TX | id=0x{frame_id:03X} data={padded.hex()}")
        except can.CanError as e:
            logger.error(f"CAN send failed | id=0x{frame_id:03X} error={e}")
            raise

    def receive_one(self, timeout: float = 1.0) -> Optional[can.Message]:
        if not self._is_connected or self._bus is None:
            raise RuntimeError("CAN bus is not connected.")
        return self._bus.recv(timeout=timeout)

    def start_listener(self, callback: Callable, stop_event=None) -> None:
        if stop_event is None:
            stop_event = threading.Event()
        logger.info(f"CAN listener started on {self._interface}/{self._channel}")
        while not stop_event.is_set():
            msg = self.receive_one(timeout=0.1)
            if msg is not None:
                try:
                    callback(msg)
                except Exception as e:
                    logger.error(f"CAN listener callback error: {e}")
        logger.info("CAN listener stopped.")

    def __repr__(self):
        status = "connected" if self._is_connected else "disconnected"
        return f"CANBus(interface={self._interface!r}, channel={self._channel!r}, status={status})"