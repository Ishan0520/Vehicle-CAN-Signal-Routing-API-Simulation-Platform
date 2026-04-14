# main.py
# The entry point. Run this file to start the entire server.
# Command: uvicorn main:app --reload

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import settings
from core.logging_config import setup_logging
from db.database import init_db
from can_sim.bus import CANBus
from ecu_sim.door_ecu import DoorECU
from ecu_sim.climate_ecu import ClimateECU
from ecu_sim.bms_ecu import BMSECU
from core.feature_dispatcher import FeatureDispatcher
from api.routes import status_routes, feature_routes

# Set up logging first, before anything else
setup_logging()
logger = logging.getLogger(__name__)

# Create shared objects (one of each, live for the whole app)
can_bus = CANBus()
door_ecu = DoorECU()
climate_ecu = ClimateECU()
bms_ecu = BMSECU()
ALL_ECUS = [door_ecu, climate_ecu, bms_ecu]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    logger.info("=" * 55)
    logger.info(f"  {settings.app_name}  v{settings.app_version}")
    logger.info("=" * 55)

    init_db()                    # create database file
    can_bus.connect()            # connect CAN sender bus
    logger.info(f"CAN bus ready: {can_bus}")

    for ecu in ALL_ECUS:         # start each ECU listener thread
        ecu.start()
        logger.info(f"ECU online: {ecu.name}")

    dispatcher = FeatureDispatcher(can_bus)  # create dispatcher

    # Attach everything so routes can access it
    app.state.can_bus = can_bus
    app.state.door_ecu = door_ecu
    app.state.climate_ecu = climate_ecu
    app.state.bms_ecu = bms_ecu
    app.state.dispatcher = dispatcher

    logger.info("-" * 55)
    logger.info("All systems ready → http://localhost:8000/docs")
    logger.info("-" * 55)

    yield  # server runs here

    # ===== SHUTDOWN =====
    logger.info("Shutting down...")
    for ecu in ALL_ECUS:
        ecu.stop()
    can_bus.disconnect()
    logger.info("Clean shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Vehicle CAN Signal Routing & API Simulation Platform",
    lifespan=lifespan,
)

app.include_router(status_routes.router)
app.include_router(feature_routes.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "platform": settings.app_name,
        "docs": "/docs",
        "health": "/status/health",
        "features": "/status/features",
        "ecu_state": "/status/ecus",
        "history": "/status/history",
    }