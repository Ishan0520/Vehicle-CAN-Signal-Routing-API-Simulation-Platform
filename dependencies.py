# api/dependencies.py
# Helper functions that give routes access to shared objects.

from fastapi import Request
from can_sim.bus import CANBus


def get_can_bus(request: Request) -> CANBus:
    return request.app.state.can_bus