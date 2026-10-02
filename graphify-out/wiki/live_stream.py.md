# live_stream.py

> 12 nodes · cohesion 0.21

## Key Concepts

- **live_stream.py** (10 connections) — `app/api/live_stream.py`
- **broadcast_event()** (7 connections) — `app/api/live_stream.py`
- **test_live_stream.py** (7 connections) — `tests/test_live_stream.py`
- **start_dispatch_simulator()** (5 connections) — `app/api/live_stream.py`
- **test_websocket_broadcast()** (5 connections) — `tests/test_live_stream.py`
- **websocket_endpoint()** (2 connections) — `app/api/live_stream.py`
- **Simulates real-time emergency dispatch events.** (1 connections) — `app/api/live_stream.py`
- **anyio** (1 connections)
- **__init__()** (1 connections) — `tests/test_live_stream.py`
- **send_json()** (1 connections) — `tests/test_live_stream.py`
- **test_websocket_connection_handshake()** (1 connections) — `tests/test_live_stream.py`
- **websocket** (1 connections)

## Relationships

- [main.py](main.py.md) (3 shared connections)
- [trace.py](trace.py.md) (2 shared connections)
- [asyncio](asyncio.md) (1 shared connections)
- [build_world](build_world.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [add_alert](add_alert.md) (1 shared connections)
- [app_services](app_services.md) (1 shared connections)
- [lifespan](lifespan.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [fastapi_testclient](fastapi_testclient.md) (1 shared connections)

## Source Files

- `app/api/live_stream.py`
- `tests/test_live_stream.py`

## Audit Trail

- EXTRACTED: 28 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*