# api/routes/status_routes.py
# All GET endpoints: health, config, ECU state, signal history, stats.

from fastapi import APIRouter, Request
from datetime import datetime
from core.config import settings
from db.signal_log import get_recent_signals, get_signals_by_feature, get_signal_stats, clear_log

router = APIRouter(prefix="/status", tags=["Status"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/config")
async def get_config():
    return {
        "can_interface": settings.can_interface,
        "can_channel": settings.can_channel,
        "can_bitrate": settings.can_bitrate,
        "dbc_file": str(settings.dbc_file_path),
    }


@router.get("/ecus")
async def get_ecu_states(request: Request):
    return {
        "door_ecu": request.app.state.door_ecu.get_state(),
        "climate_ecu": request.app.state.climate_ecu.get_state(),
        "bms_ecu": request.app.state.bms_ecu.get_state(),
    }


@router.get("/features")
async def list_features(request: Request):
    dispatcher = request.app.state.dispatcher
    return {"total": len(dispatcher.list_features()), "features": dispatcher.list_features()}


@router.get("/history")
async def get_signal_history(feature: str = None, limit: int = 50):
    limit = max(1, min(limit, 500))
    if feature:
        records = get_signals_by_feature(feature_name=feature, limit=limit)
    else:
        records = get_recent_signals(limit=limit)
    return {"count": len(records), "filter": feature or "none", "records": records}


@router.get("/stats")
async def get_stats():
    return get_signal_stats()


@router.delete("/history")
async def clear_history():
    deleted = clear_log()
    return {"message": f"Cleared {deleted} records from signal log."}