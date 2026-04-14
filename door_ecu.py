# ecu_sim/door_ecu.py
# Simulates the Door ECU.
# Listens for CAN message 0x210 and reacts to lock/window commands.

import logging
from ecu_sim.base_ecu import BaseECU

logger = logging.getLogger(__name__)

LOCK_STATES = {0: "UNLOCKED", 1: "LOCKED", 2: "DOUBLE_LOCKED"}
WINDOW_STATES = {0: "CLOSED", 1: "OPEN", 2: "HALF_OPEN"}


class DoorECU(BaseECU):
    LISTEN_IDS = {0x210}

    def __init__(self):
        super().__init__(name="DoorECU")
        self.state = {"door_lock": "LOCKED", "door_window": "CLOSED"}

    def on_message(self, message_id: int, signals: dict, raw: bytes) -> None:
        changes = []

        if "DOOR_LOCK_CMD" in signals:
            new_state = LOCK_STATES.get(int(signals["DOOR_LOCK_CMD"]), "UNKNOWN")
            if new_state != self.state["door_lock"]:
                old = self.state["door_lock"]
                self.state["door_lock"] = new_state
                changes.append(f"lock: {old} → {new_state}")

        if "DOOR_WINDOW_CMD" in signals:
            new_state = WINDOW_STATES.get(int(signals["DOOR_WINDOW_CMD"]), "UNKNOWN")
            if new_state != self.state["door_window"]:
                old = self.state["door_window"]
                self.state["door_window"] = new_state
                changes.append(f"window: {old} → {new_state}")

        if changes:
            logger.info(f"[DoorECU] {' | '.join(changes)}")
            print(f"  [DoorECU]  {' | '.join(changes)}")