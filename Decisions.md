# Design Decisions

Key architectural and technology choices made during this project, and the reasoning behind each.

---

## Why FastAPI (not Flask or Django)?

**FastAPI** was chosen for three specific reasons, not just familiarity:

1. **Automatic schema validation via Pydantic.** Every API input is validated against a typed model before any code runs. This mirrors how production vehicle APIs enforce message contract compliance — malformed inputs are rejected at the boundary, not discovered inside the pipeline.

2. **Auto-generated interactive documentation.** `/docs` renders a live Swagger UI from the code itself, with no extra work. For a portfolio project reviewed by engineers, being able to run and test the API in a browser without writing a client is meaningful.

3. **Async lifespan management.** FastAPI's `asynccontextmanager` lifespan pattern gave a clean startup/shutdown hook for connecting the CAN bus and starting ECU threads before serving requests — and tearing everything down in the correct order on exit.

Flask would have worked technically. Django would have been overengineered. FastAPI fit the problem.

---

## Why simulation instead of real CAN hardware?

The goal was to simulate the *logic* of a CAN signal pipeline, not the *physics* of a CAN wire. Using `python-can` with `interface="virtual"` achieves this with three advantages:

1. **Zero hardware dependency.** Anyone can clone the repo and run the full system in under 2 minutes on any OS. Real CAN hardware (SocketCAN on Linux, PEAK PCAN, Vector CANalyzer) introduces setup complexity that obscures the architecture.

2. **Identical code path to real hardware.** The `CANBus` class takes `interface` and `channel` as config values. To run on real hardware, change `interface="virtual"` to `interface="socketcan"` in `config.py`. Nothing else changes — not the dispatcher, not the ECU simulators, not the DBC parser. The abstraction is real.

3. **Correct broadcast semantics.** `python-can` virtual interface behaves like a real CAN bus: any process connected to the same named channel receives all frames. The ECU simulators genuinely receive and process frames they didn't send — this is not mocked.

The tradeoff: timing characteristics and bus load are not simulated. This is acceptable for the goal of demonstrating signal routing and ECU behaviour.

---

## Why this modular architecture (5 separate layers)?

The alternative was simpler: one file that takes a feature name, looks up the signal, encodes it, and sends it. That would have been ~100 lines.

The modular structure was a deliberate choice for three reasons:

**1. Each layer can be replaced independently.**

The mapping engine reads from JSON today. In a real vehicle program, it might read from a JIRA ticket database or a requirements management tool (e.g. DOORS). Replacing it requires zero changes to the DBC parser or the CAN bus layer.

The CAN bus uses virtual interface today. Replacing it with SocketCAN, a CAN-over-IP bridge, or a proprietary hardware driver requires zero changes to the ECU simulators or the API.

**2. Each layer can be tested independently.**

You can unit test the mapping engine by passing feature names and checking outputs — no CAN bus needed. You can test the DBC parser by checking encode/decode round-trips — no API needed. This is how real system software is tested: at each layer boundary, not only end-to-end.

**3. It mirrors how the real engineering work was structured.**

At Rivian, different teams owned different layers:
- Product teams defined features
- Systems engineers defined signal mappings
- Network architects owned the DBC
- Domain teams (Door, BMS, Climate) owned ECU behaviour

The five-layer architecture reflects that organisational reality. A TPM working on this system needs to understand where each team's ownership starts and ends — and where the integration risks live. Building it this way made those boundaries concrete.

---

## Why SQLite for the signal log?

Two reasons:

1. **Zero infrastructure.** No database server to spin up, no connection string to configure, no Docker container required. The database is a single file. For a project whose purpose is demonstrating signal routing logic, introducing Postgres would be noise.

2. **It's the right tool for an audit log.** The signal log is append-heavy, read occasionally, and never requires complex joins. SQLite handles this workload correctly. The schema has two indexes (timestamp, feature_name) for the query patterns actually used.

If this project were deployed as a cloud service logging millions of signals per hour, the right answer is a time-series database (InfluxDB, TimescaleDB) or a streaming pipeline (Kafka + S3). That's documented in [`future-work.md`](future-work.md).

---

## Why Python threading (not asyncio) for ECU listeners?

The ECU simulators use `threading.Thread`, not `asyncio` coroutines.

`python-can`'s receive loop is a **blocking** call (`bus.recv(timeout=...)`). Blocking calls don't play nicely with `asyncio`'s event loop — wrapping them requires `loop.run_in_executor()`, which adds complexity with no benefit here.

Threads are simpler for this pattern: each ECU is an independent process (in the conceptual sense — it has its own bus connection, its own state, its own loop). The `daemon=True` flag ensures threads exit automatically when the main process stops, avoiding the need for explicit join logic in most cases.

The only threading concern is reading `self.state` from the API (main thread) while the ECU thread writes it. For the current use case (infrequent reads, simple dict), Python's GIL provides sufficient protection. A production system would use `threading.Lock()` or `threading.RLock()` around state updates.

---

## Why a `BaseECU` abstract class?

The three ECUs share 90% of their code: connecting to the bus, running a receive loop, filtering by message ID, decoding with the DBC parser. Only `on_message()` differs.

Without `BaseECU`, adding a fourth ECU (e.g. a Lights ECU) means copying 60 lines of boilerplate. With it, adding a fourth ECU means:

1. Create `ecu_sim/lights_ecu.py`
2. Inherit from `BaseECU`
3. Set `LISTEN_IDS = {0x240}`
4. Implement `on_message()`

That's it. This is the **Template Method** design pattern: define the algorithm skeleton in the base class, let subclasses fill in the specific steps.
