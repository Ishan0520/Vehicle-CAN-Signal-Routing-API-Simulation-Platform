# Demo

Complete API request/response examples with expected server output.

**Prerequisites:** Server running at `http://localhost:8000`

```bash
uvicorn main:app --reload
```

---

## Startup Output

```
=======================================================
  Vehicle CAN Signal Routing Platform  v0.1.0
=======================================================
10:00:01 | INFO | db.database              | Database initialised: db/signals.db
10:00:01 | INFO | can_sim.bus              | CAN bus connected | interface=virtual channel=vcan0
10:00:01 | INFO | ecu_sim.base_ecu         | [DoorECU] started — listening for IDs: ['0x210']
10:00:01 | INFO | ecu_sim.base_ecu         | [ClimateECU] started — listening for IDs: ['0x220']
10:00:01 | INFO | ecu_sim.base_ecu         | [BMSECU] started — listening for IDs: ['0x230']
10:00:01 | INFO | core.feature_dispatcher  | FeatureDispatcher ready | features=10
-------------------------------------------------------
All systems ready → http://localhost:8000/docs
-------------------------------------------------------
```

---

## Use Case 1 — Unlock Door

**Request:**
```bash
curl -X POST http://localhost:8000/feature/unlock_door \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "unlock_door", "value": 0}'
```

**Response:**
```json
{
  "success": true,
  "feature_name": "unlock_door",
  "value": 0.0,
  "message": "Signal 'DOOR_LOCK_CMD' = 0.0 on 'DOOR_CONTROL' (ID=0x210). Frame: 0000000000000000",
  "can_message_id": 528,
  "can_signal": "DOOR_LOCK_CMD",
  "timestamp": "2024-01-15T10:00:05.123456"
}
```

**Server log:**
```
10:00:05 | INFO | core.feature_dispatcher  | Dispatched | feature='unlock_door' signal=DOOR_LOCK_CMD value=0.0 frame=0x210/0000000000000000
  [DoorECU]  lock: LOCKED → UNLOCKED
```

**ECU state after (`GET /status/ecus`):**
```json
{
  "door_ecu": {
    "door_lock": "UNLOCKED",
    "door_window": "CLOSED"
  }
}
```

---

## Use Case 2 — Set Cabin Temperature

**Request:**
```bash
curl -X POST http://localhost:8000/feature/set_temperature \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "set_temperature", "value": 24.5}'
```

**Response:**
```json
{
  "success": true,
  "feature_name": "set_temperature",
  "value": 24.5,
  "message": "Signal 'CABIN_TEMP_SET' = 24.5 on 'CLIMATE_CONTROL' (ID=0x220). Frame: 1300000000000000",
  "can_message_id": 544,
  "can_signal": "CABIN_TEMP_SET",
  "timestamp": "2024-01-15T10:00:08.445123"
}
```

**Server log:**
```
10:00:08 | INFO | core.feature_dispatcher  | Dispatched | feature='set_temperature' signal=CABIN_TEMP_SET value=24.5 frame=0x220/1300000000000000
  [ClimateECU]  temp: 22.0°C → 24.5°C
```

> Frame byte `0x13` = 19 decimal. Verify: `19 × 0.5 + 15.0 = 24.5°C` ✓

---

## Use Case 3 — Start Charging

**Request:**
```bash
curl -X POST http://localhost:8000/feature/start_charging \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "start_charging", "value": 1}'
```

**Response:**
```json
{
  "success": true,
  "feature_name": "start_charging",
  "value": 1.0,
  "message": "Signal 'CHARGE_ENABLE' = 1.0 on 'BMS_CONTROL' (ID=0x230). Frame: 0100000000000000",
  "can_message_id": 560,
  "can_signal": "CHARGE_ENABLE",
  "timestamp": "2024-01-15T10:00:12.001234"
}
```

**Server log:**
```
10:00:12 | INFO | core.feature_dispatcher  | Dispatched | feature='start_charging' signal=CHARGE_ENABLE value=1.0 frame=0x230/0100000000000000
  [BMSECU]  charge: IDLE → CHARGING
```

---

## Use Case 4 — Set Charge Current Limit

**Request:**
```bash
curl -X POST http://localhost:8000/feature/set_charge_limit \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "set_charge_limit", "value": 48.0}'
```

**Response:**
```json
{
  "success": true,
  "feature_name": "set_charge_limit",
  "value": 48.0,
  "message": "Signal 'CHARGE_CURRENT_LIMIT' = 48.0 on 'BMS_CONTROL' (ID=0x230). Frame: 0060000000000000",
  "can_message_id": 560,
  "can_signal": "CHARGE_CURRENT_LIMIT"
}
```

**Server log:**
```
  [BMSECU]  current limit: 0.0A → 48.0A
```

---

## Use Case 5 — Full System State

After running the four commands above:

```bash
curl http://localhost:8000/status/ecus
```

```json
{
  "door_ecu": {
    "door_lock": "UNLOCKED",
    "door_window": "CLOSED"
  },
  "climate_ecu": {
    "cabin_temp_set": 24.5,
    "ac_enabled": false,
    "fan_speed": 0
  },
  "bms_ecu": {
    "charging": true,
    "charge_current_limit": 48.0,
    "soc_requested": false,
    "soc_percent": 75.0
  }
}
```

---

## Signal History

```bash
curl http://localhost:8000/status/history
```

```json
{
  "count": 4,
  "filter": "none",
  "records": [
    {
      "id": 4,
      "feature_name": "set_charge_limit",
      "signal_name": "CHARGE_CURRENT_LIMIT",
      "signal_value": 48.0,
      "can_message_id": 560,
      "can_message_hex": "0x230",
      "raw_bytes": "0060000000000000",
      "success": true,
      "timestamp": "2024-01-15T10:00:15.334"
    },
    {
      "id": 3,
      "feature_name": "start_charging",
      "signal_name": "CHARGE_ENABLE",
      "signal_value": 1.0,
      "can_message_id": 560,
      "can_message_hex": "0x230",
      "raw_bytes": "0100000000000000",
      "success": true,
      "timestamp": "2024-01-15T10:00:12.001"
    }
  ]
}
```

**Filter by feature:**
```bash
curl "http://localhost:8000/status/history?feature=unlock_door&limit=5"
```

---

## Aggregate Stats

```bash
curl http://localhost:8000/status/stats
```

```json
{
  "total_signals_sent": 4,
  "successful": 4,
  "failed": 0,
  "by_feature": {
    "set_charge_limit": 1,
    "start_charging": 1,
    "set_temperature": 1,
    "unlock_door": 1
  },
  "last_signal_at": "2024-01-15T10:00:15.334"
}
```

---

## Error Cases

**Unknown feature:**
```bash
curl -X POST http://localhost:8000/feature/fly_the_car \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "fly_the_car", "value": 1}'
```

```json
{
  "detail": "Feature 'fly_the_car' not found in mapping.\nAvailable features: ['lock_door', 'request_soc', 'set_ac', 'set_charge_limit', 'set_fan_speed', 'set_temperature', 'set_window', 'start_charging', 'stop_charging', 'unlock_door']"
}
```
HTTP 400.

**Invalid discrete value:**
```bash
curl -X POST http://localhost:8000/feature/unlock_door \
  -H "Content-Type: application/json" \
  -d '{"feature_name": "unlock_door", "value": 99}'
```

```json
{
  "detail": "Feature 'unlock_door': value 99.0 is not valid.\nAllowed values: ['0', '1', '2']\nHint: 0=unlock, 1=lock, 2=double-lock"
}
```
HTTP 400.

---

## All Available Features

```bash
curl http://localhost:8000/status/features
```

```json
{
  "total": 10,
  "features": [
    { "feature_name": "unlock_door",     "signal_name": "DOOR_LOCK_CMD",         "message_name": "DOOR_CONTROL",    "value_description": "0=unlock, 1=lock, 2=double-lock" },
    { "feature_name": "lock_door",       "signal_name": "DOOR_LOCK_CMD",         "message_name": "DOOR_CONTROL",    "value_description": "0=unlock, 1=lock, 2=double-lock" },
    { "feature_name": "set_window",      "signal_name": "DOOR_WINDOW_CMD",       "message_name": "DOOR_CONTROL",    "value_description": "0=closed, 1=open, 2=half-open" },
    { "feature_name": "set_temperature", "signal_name": "CABIN_TEMP_SET",        "message_name": "CLIMATE_CONTROL", "value_description": "Temperature in °C, range 15.0–35.0" },
    { "feature_name": "set_ac",          "signal_name": "AC_ENABLE",             "message_name": "CLIMATE_CONTROL", "value_description": "0=off, 1=on" },
    { "feature_name": "set_fan_speed",   "signal_name": "FAN_SPEED",             "message_name": "CLIMATE_CONTROL", "value_description": "Integer 0–10" },
    { "feature_name": "start_charging",  "signal_name": "CHARGE_ENABLE",         "message_name": "BMS_CONTROL",     "value_description": "0=stop, 1=start" },
    { "feature_name": "stop_charging",   "signal_name": "CHARGE_ENABLE",         "message_name": "BMS_CONTROL",     "value_description": "0=stop, 1=start" },
    { "feature_name": "set_charge_limit","signal_name": "CHARGE_CURRENT_LIMIT",  "message_name": "BMS_CONTROL",     "value_description": "Current in Amps, range 0–100A" },
    { "feature_name": "request_soc",     "signal_name": "SOC_REQUEST",           "message_name": "BMS_CONTROL",     "value_description": "1=request SOC" }
  ]
}
```
