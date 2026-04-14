# ecu_sim/bms_ecu.py
# Simulates the Battery Management System (BMS) ECU.
# Listens for CAN message 0x230.

import logging
from ecu_sim.base_ecu import BaseECU

logger = logging.getLogger(__name__)


class BMSECU(BaseECU):
    LISTEN_IDS = {0x230}

    def __init__(self):
        super().__init__(name="BMSECU")
        self.state = {
            "charging": False,
            "charge_current_limit": 0.0,
            "soc_requested": False,
            "soc_percent": 75.0,
        }

    def on_message(self, message_id: int, signals: dict, raw: bytes) -> None:
        changes = []

        if "CHARGE_ENABLE" in signals:
            new_charging = bool(int(signals["CHARGE_ENABLE"]))
            if new_charging != self.state["charging"]:
                self.state["charging"] = new_charging
                changes.append(f"charge: {'IDLE' if not new_charging else 'CHARGING'}")

        if "CHARGE_CURRENT_LIMIT" in signals:
            new_limit = round(float(signals["CHARGE_CURRENT_LIMIT"]), 1)
            if new_limit != self.state["charge_current_limit"]:
                old = self.state["charge_current_limit"]
                self.state["charge_current_limit"] = new_limit
                changes.append(f"current limit: {old}A → {new_limit}A")

        if "SOC_REQUEST" in signals:
            if int(signals["SOC_REQUEST"]) == 1:
                self.state["soc_requested"] = True
                changes.append(f"SOC requested → {self.state['soc_percent']}%")

        if changes:
            logger.info(f"[BMSECU] {' | '.join(changes)}")
            print(f"  [BMSECU]  {' | '.join(changes)}")