import asyncio
import random
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_CONNECTIONS = set()

# Simulated emergency dispatch events
_INCIDENTS = [
    {"crime_type": "CHAIN_SNATCHING", "zone": "Rajajinagar", "message": "Incident: Chain snatching reported near Rajajinagar 3rd Block. Two suspects on a Pulsar motorcycle. Patrolling units dispatched."},
    {"crime_type": "THEFT", "zone": "Whitefield", "message": "Incident: Night burglary alarm at electronic shop in Whitefield. Unit 4B investigating."},
    {"crime_type": "ROBBERY", "zone": "Bengaluru North", "message": "Incident: Cash-van robbery attempt foiled near Hebbal flyover. One suspect detained."},
    {"crime_type": "CYBERCRIME", "zone": "Jayanagar", "message": "Incident: Phishing complaint registered at Jayanagar PS. OTP fraud involving INR 50k."},
    {"crime_type": "BURGLARY", "zone": "Malleshwaram", "message": "Incident: Housebreak reported in Malleshwaram 15th cross. Crime scene team dispatched."},
]

async def broadcast_event(event: dict):
    if not _CONNECTIONS:
        return
    # Make copy to avoid mutation during iteration
    active = list(_CONNECTIONS)
    for ws in active:
        try:
            await ws.send_json(event)
        except Exception:
            _CONNECTIONS.discard(ws)

async def broadcast_reasoning_step(step_entry: dict):
    event = {
        "type": "reasoning_trace",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent": step_entry.get("agent"),
        "step": step_entry.get("step"),
        "input_digest": step_entry.get("input_digest"),
        "output_digest": step_entry.get("output_digest"),
        "ms": step_entry.get("ms"),
        "session_id": step_entry.get("session_id")
    }
    await broadcast_event(event)

async def start_dispatch_simulator():
    """Simulates real-time emergency dispatch events."""
    while True:
        await asyncio.sleep(random.randint(4, 7))
        if not _CONNECTIONS:
            continue
        incident = random.choice(_INCIDENTS)
        event = {
            "type": "emergency_dispatch",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "crime_type": incident["crime_type"],
            "zone": incident["zone"],
            "message": incident["message"],
            "dispatch_status": "dispatched"
        }
        await broadcast_event(event)

@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _CONNECTIONS.add(websocket)
    try:
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "active_listeners": len(_CONNECTIONS)
        })
        while True:
            # Keep read open to detect client disconnection
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _CONNECTIONS.discard(websocket)
