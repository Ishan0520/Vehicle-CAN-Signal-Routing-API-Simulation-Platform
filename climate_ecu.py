# ecu_sim/climate_ecu.py
# Simulates the Climate Control ECU.
# Listens for CAN message 0x220.

import logging
from ecu_sim.base_ecu import BaseECU

logger = logging.getLogger(__name__)


class ClimateECU(BaseECU):
    LISTEN_IDS = {0x220}

    def __init__(self):
        super().__init__(name="ClimateECU")
        self.state = {"cabin_temp_set": 22.0, "ac_enabled": False, "fan_speed": 0}

    def on_message(self, message_id: int, signals: dict, raw: bytes) -> None:
        changes = []

        if "CABIN_TEMP_SET" in signals:
            new_temp = round(float(signals["CABIN_TEMP_SET"]), 1)
            if new_temp != self.state["cabin_temp_set"]:
                old = self.state["cabin_temp_set"]
                self.state["cabin_temp_set"] = new_temp
                changes.append(f"temp: {old}°C → {new_temp}°C")

        if "AC_ENABLE" in signals:
            new_ac = bool(int(signals["AC_ENABLE"]))
            if new_ac != self.state["ac_enabled"]:
                self.state["ac_enabled"] = new_ac
                changes.append(f"AC: {'ON' if new_ac else 'OFF'}")

        if "FAN_SPEED" in signals:
            new_fan = int(signals["FAN_SPEED"])
            if new_fan != self.state["fan_speed"]:
                old = self.state["fan_speed"]
                self.state["fan_speed"] = new_fan
                changes.append(f"fan: {old} → {new_fan}")

        if changes:
            logger.info(f"[ClimateECU] {' | '.join(changes)}")
            print(f"  [ClimateECU]  {' | '.join(changes)}")