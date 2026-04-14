# core/feature_dispatcher.py
# The orchestrator. Takes a feature name, calls mapping, DBC, CAN, and DB.
# This is the ONLY file that knows all the other pieces exist.

import logging
from datetime import datetime

from mapping.engine import MappingEngine
from dbc.parser import DBCParser
from can_sim.bus import CANBus
from models.feature import FeatureResponse
from core.config import settings
from db.signal_log import log_signal

logger = logging.getLogger(__name__)


class FeatureDispatcher:
    def __init__(self, can_bus: CANBus):
        self._bus = can_bus
        self._mapping = MappingEngine()
        self._parser = DBCParser(settings.dbc_file_path)
        logger.info(f"FeatureDispatcher ready | features={len(self._mapping)} | bus={self._bus}")

    def dispatch(self, feature_name: str, requested_value: float) -> FeatureResponse:
        # Step 1: Resolve mapping
        try:
            entry, final_value = self._mapping.resolve(feature_name, requested_value)
        except (KeyError, ValueError) as e:
            logger.warning(f"Mapping failed: {feature_name!r} → {e}")
            _safe_log(feature_name=feature_name, signal_name="UNKNOWN",
                      signal_value=requested_value, can_message_id=0, raw_bytes="", success=False)
            return FeatureResponse(success=False, feature_name=feature_name,
                                   value=requested_value, message=str(e), timestamp=datetime.utcnow())

        # Step 2: Encode via DBC
        try:
            frame_id, frame_data = self._parser.encode_signal(
                message_name=entry.message_name,
                signal_name=entry.signal_name,
                value=final_value,
            )
        except KeyError as e:
            logger.error(f"DBC encode failed: {feature_name!r} → {e}")
            return FeatureResponse(success=False, feature_name=feature_name,
                                   value=requested_value, message=f"DBC encoding error: {e}",
                                   timestamp=datetime.utcnow())

        # Step 3: Send on CAN bus
        try:
            self._bus.send(frame_id=frame_id, data=frame_data)
        except Exception as e:
            logger.error(f"CAN send failed: {feature_name!r} → {e}")
            _safe_log(feature_name=feature_name, signal_name=entry.signal_name,
                      signal_value=final_value, can_message_id=frame_id,
                      raw_bytes=frame_data.hex(), success=False)
            return FeatureResponse(success=False, feature_name=feature_name,
                                   value=requested_value, message=f"CAN bus error: {e}",
                                   timestamp=datetime.utcnow())

        # Step 4: Log to DB
        _safe_log(feature_name=feature_name, signal_name=entry.signal_name,
                  signal_value=final_value, can_message_id=frame_id,
                  raw_bytes=frame_data.hex(), success=True)

        # Step 5: Return response
        message = (
            f"Signal '{entry.signal_name}' = {final_value} "
            f"on '{entry.message_name}' (ID=0x{frame_id:03X}). "
            f"Frame: {frame_data.hex()}"
        )
        logger.info(f"Dispatched | feature={feature_name!r} signal={entry.signal_name} "
                    f"value={final_value} frame=0x{frame_id:03X}/{frame_data.hex()}")

        return FeatureResponse(
            success=True, feature_name=feature_name, value=final_value,
            message=message, timestamp=datetime.utcnow(),
            can_message_id=frame_id, can_signal=entry.signal_name,
        )

    def list_features(self) -> list[dict]:
        return self._mapping.list_features()

    def __repr__(self):
        return f"FeatureDispatcher(features={len(self._mapping)}, bus={self._bus})"


def _safe_log(**kwargs) -> None:
    try:
        log_signal(**kwargs)
    except Exception as e:
        logger.error(f"DB log failed (non-fatal): {e}")