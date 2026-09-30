import pytest
from fastapi.testclient import TestClient
from main import app
from app.api.live_stream import broadcast_event, _CONNECTIONS

client = TestClient(app)

def test_websocket_connection_handshake():
    with client.websocket_connect("/api/stream/events") as websocket:
        # First message should be the connection status handshake
        data = websocket.receive_json()
        assert data["type"] == "connection_status"
        assert data["status"] == "connected"
        assert "active_listeners" in data

@pytest.mark.anyio
async def test_websocket_broadcast():
    # Simulate an active connection by adding a mock/spy to _CONNECTIONS
    class MockWebSocket:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
            
    ws = MockWebSocket()
    _CONNECTIONS.add(ws)
    try:
        test_event = {"type": "test_event", "val": 42}
        await broadcast_event(test_event)
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "test_event"
        assert ws.sent[0]["val"] == 42
    finally:
        _CONNECTIONS.discard(ws)
