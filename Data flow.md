# Data Flow

Step-by-step trace of a real request through the full pipeline.

---

## Example: `POST /feature/unlock_door` with `value: 0`

---

### Step 1 — HTTP Request received

```
POST /feature/unlock_door
Content-Type: application/json

{
  "feature_name": "unlock_door",
  "value": 0
}
```

FastAPI parses the body against `FeatureRequest` (Pydantic model).
Validation checks: `feature_name` is a non-empty string, `value` is a float.
The route calls `dispatcher.dispatch("unlock_door", 0.0)`.

---

### Step 2 — Mapping Engine resolves the feature

```
MappingEngine.resolve("unlock_door", 0.0)
```

Looks up `"unlock_door"` in `feature_map.json`:

```json
{
  "unlock_door": {
    "message_name": "DOOR_CONTROL",
    "signal_name":  "DOOR_LOCK_CMD",
    "value_map":    { "0": 0, "1": 1, "2": 2 },
    "default_value": 0
  }
}
```

Value resolution:
- `value_map` is non-empty → discrete mode
- Key `"0"` exists → mapped value = `0`

Returns:
```
MappingEntry(message_name="DOOR_CONTROL", signal_name="DOOR_LOCK_CMD")
final_value = 0.0
```

---

### Step 3 — DBC Parser encodes the signal

```
DBCParser.encode_signal("DOOR_CONTROL", "DOOR_LOCK_CMD", 0.0)
```

Loads signal definition from `vehicle.dbc`:
```
SG_ DOOR_LOCK_CMD : 0|2@1+ (1,0) [0|3] "" DOOR_ECU
```
- Start bit: 0, Length: 2 bits, Scale: 1, Offset: 0
- Raw value = (0.0 - 0) / 1 = **0**

`cantools` packs bit value `0` into an 8-byte frame with `padding=True`:

```
frame_id = 528 (0x210)
data     = b'\x00\x00\x00\x00\x00\x00\x00\x00'
hex      = "0000000000000000"
```

---

### Step 4 — CAN Bus sends the frame

```
CANBus.send(frame_id=528, data=b'\x00\x00\x00\x00\x00\x00\x00\x00')
```

Constructs a `can.Message`:
```python
can.Message(
    arbitration_id = 0x210,
    data           = b'\x00\x00\x00\x00\x00\x00\x00\x00',
    is_extended_id = False
)
```

`python-can` puts this frame onto the virtual channel `vcan0`.
Every process connected to `vcan0` receives it — including all three ECU listener threads.

---

### Step 5 — ECU Simulators receive the broadcast

All three ECU threads are running `receive_one(timeout=0.1)` in a loop.

**DoorECU** (listening for `0x210`):
- Receives frame with `arbitration_id = 0x210` ✓ — match
- Calls `DBCParser.decode_message(528, b'\x00...\x00')`
- Returns: `{"DOOR_LOCK_CMD": 0.0, "DOOR_WINDOW_CMD": 0.0}`
- Passes decoded signals to `on_message()`

**ClimateECU** and **BMSECU**:
- Receive the same frame
- `0x210` not in their `LISTEN_IDS` → silently ignored

---

### Step 6 — DoorECU processes the message

```python
DoorECU.on_message(message_id=0x210, signals={"DOOR_LOCK_CMD": 0.0, ...})
```

- `DOOR_LOCK_CMD = 0` → maps to `"UNLOCKED"`
- Current state: `door_lock = "LOCKED"`
- State changed → update and log:

```
[DoorECU] lock: LOCKED → UNLOCKED
```

`self.state` is now:
```json
{ "door_lock": "UNLOCKED", "door_window": "CLOSED" }
```

---

### Step 7 — Signal logged to SQLite

Back in the dispatcher, after the send:

```python
log_signal(
    feature_name   = "unlock_door",
    signal_name    = "DOOR_LOCK_CMD",
    signal_value   = 0.0,
    can_message_id = 528,
    raw_bytes      = "0000000000000000",
    success        = True
)
```

New row inserted into `signal_log` table with timestamp.

---

### Step 8 — Response returned to caller

```json
{
  "success": true,
  "feature_name": "unlock_door",
  "value": 0.0,
  "message": "Signal 'DOOR_LOCK_CMD' = 0.0 on 'DOOR_CONTROL' (ID=0x210). Frame: 0000000000000000",
  "can_message_id": 528,
  "can_signal": "DOOR_LOCK_CMD",
  "timestamp": "2024-01-15T10:23:45.123456"
}
```

HTTP 200.

---

## Summary: Full Flow

```
POST /feature/unlock_door  {value: 0}
        │
        ▼
  FastAPI route             validates FeatureRequest schema
        │
        ▼
  FeatureDispatcher         orchestrates pipeline
        │
        ▼
  MappingEngine             "unlock_door" → DOOR_CONTROL / DOOR_LOCK_CMD / 0.0
        │
        ▼
  DBCParser                 encode DOOR_LOCK_CMD=0 → frame 0x210: 0000000000000000
        │
        ▼
  CANBus (sender)           python-can puts frame on vcan0
        │
        ├──────────────────────────────────────────┐
        ▼                                          ▼
  DoorECU thread            ClimateECU / BMSECU threads
  0x210 → match             0x210 → not in LISTEN_IDS → ignored
  decode → DOOR_LOCK_CMD=0
  state: LOCKED → UNLOCKED
        │
        ▼
  SQLite log                INSERT INTO signal_log ...
        │
        ▼
  HTTP 200                  FeatureResponse { success: true, ... }
```

---

## Scale/Offset Encoding — Why 0x13 for 24.5°C

For `set_temperature` with value `24.5`:

```
DBC signal: CABIN_TEMP_SET scale=0.5, offset=15.0
Raw value  = (24.5 - 15.0) / 0.5 = 19 = 0x13
Frame byte = 0x13 at bit position 0
```

This is why the raw frame for `set_temperature=24.5` is `1300000000000000`.

The inverse (decode) confirms: `19 × 0.5 + 15.0 = 24.5°C`.

This scale/offset pattern is how all analog values (temperature, current, voltage) are transmitted as integers on the CAN wire. The DBC file is the translation key.
