# Future Work

Planned extensions in rough priority order. Each item notes what it would demonstrate beyond the current implementation.

---

## Near-Term

### Real Hardware Integration (SocketCAN)

The architecture already supports this — `CANBus` accepts `interface` and `channel` as config values.

**What's needed:**
- Linux host with `socketcan` kernel module
- CAN transceiver hardware (e.g. Raspberry Pi + MCP2515, or a USB-CAN adapter like PEAK PCAN-USB)
- Change `can_interface = "virtual"` → `"socketcan"` and `can_channel = "vcan0"` → `"can0"` in config

**What this unlocks:**
- Actual frame timing on a real CAN bus (500 kbps)
- Integration with real OBD-II diagnostic tools (e.g. SavvyCAN, CANalyzer)
- Validation that signal encoding is correct at the wire level

**Scope:** Config change + hardware setup. Zero code changes required.

---

### WebSocket Live ECU Feed

Add a WebSocket endpoint that streams ECU state changes in real time to a browser client.

```
GET /ws/ecu-stream
→ {"ecu": "DoorECU", "change": "lock: LOCKED → UNLOCKED", "timestamp": "..."}
```

**Why:** Demonstrates async event streaming, which is a common pattern in vehicle telemetry systems. Also makes the demo significantly more visual — watching state change in a browser as you send commands.

**Stack addition:** FastAPI WebSocket + simple HTML/JS client

---

### Fault Injection Mode

Add a configurable fault layer that can simulate failure conditions:

- **ECU non-response:** Drop frames addressed to a specific ECU (simulates a disconnected node)
- **Signal out-of-range:** Inject a corrupted value into a decoded signal
- **Bus-off condition:** Simulate a CAN bus error state
- **Message ID conflict:** Send two messages with the same ID from different senders

**Why this matters:** In real vehicle programs, fault injection testing is mandatory. Understanding how the system behaves under these conditions — and whether the API layer surfaces them correctly — is a core TPM concern.

---

## Medium-Term

### Multi-Vehicle Profile Support

Currently the system loads one DBC file and one feature map at startup.

**Extension:** Support multiple vehicle profiles (e.g. `vehicle_a.dbc` + `feature_map_a.json` for sedan, `vehicle_b.dbc` + `feature_map_b.json` for truck) switchable via API or config.

```bash
# Start with a specific vehicle profile
uvicorn main:app --env-file .env.vehicle_b
```

**Why this matters:** In real programs, the same platform team often supports multiple vehicle lines with different DBC versions. The architecture already supports this — the DBC path and feature map path are config values.

---

### DBC Hot-Reload

Watch `vehicle.dbc` for file changes and reload the parser without restarting the server.

**Use case:** During active DBC development, signal definitions change frequently. A hot-reload mechanism means engineers can update the DBC and immediately test the new signals without a service restart — closer to real ECU development workflows.

**Stack addition:** `watchdog` library for file system events

---

### Signal Validation Layer

Before encoding, validate that the requested value falls within the signal's defined min/max range (from the DBC).

Currently, `cantools` encodes out-of-range values with `strict=False`. A validation layer would:
- Reject values outside DBC-defined bounds with a clear error
- Warn on values close to limits
- Log range violations for audit

This mirrors how real vehicle software handles commanded values from upper-layer systems.

---

## Longer-Term

### Cloud Deployment + Telemetry

Deploy the platform as a cloud service and stream signal events to a telemetry backend.

**Architecture:**
```
Vehicle API  →  Kafka topic  →  InfluxDB (time-series)
                                    └── Grafana dashboard
```

**Why:** Demonstrates the cloud-connected vehicle architecture pattern used by OEMs like Rivian, Tesla, and GM — where vehicle signals are mirrored to a cloud backend for fleet monitoring, remote diagnostics, and OTA trigger conditions.

---

### Prometheus Metrics + Grafana

Expose a `/metrics` endpoint (Prometheus format) with:
- `signals_dispatched_total` (counter, labelled by feature)
- `signals_failed_total` (counter)
- `can_frame_send_latency_ms` (histogram)
- `ecu_state_changes_total` (counter, labelled by ECU)

Pre-built Grafana dashboard in `docs/grafana/`.

**Why:** Observability is a first-class concern in any production system. A TPM reviewing a platform like this would immediately ask "how do we know it's healthy?" — this answers that.

---

### REST → SOME/IP or AUTOSAR Migration Path

Document and prototype the migration from a REST API trigger model to AUTOSAR-compliant service communication (SOME/IP).

SOME/IP is the standard used in most modern production vehicle software stacks (especially AUTOSAR Adaptive). The current architecture — feature request → signal routing → CAN frame — maps directly to the SOME/IP service invocation model.

**Why:** Shows awareness of where this simulation sits relative to production automotive software stacks, and what would need to change to move from prototype to production-grade.

---

*Have a suggestion? Open an issue or PR.*
