"""Alerts survive a restart: the Alerts screen is not empty until the next scan."""
import importlib


def _reload(monkeypatch, mode, path):
    monkeypatch.setenv("ANTAR_ALERTS", mode)
    monkeypatch.setenv("ANTAR_ALERTS_DB", str(path))
    from app.services import alerts_store
    return importlib.reload(alerts_store)


def test_alerts_survive_a_restart(tmp_path, monkeypatch):
    db = tmp_path / "a.db"
    store = _reload(monkeypatch, "file", db)
    store.replace_all([{"alert_type": "spike", "zone": "Mysuru City", "crime_type": "Theft", "z_score": 3.1, "status": "new"}])
    store.add_alert({"watch_id": "W1", "zone": "Hassan", "z_score": 0, "message": "watch tripped"})
    store.add_alert({"watch_id": "W1", "zone": "Hassan", "z_score": 0, "message": "still tripped"})   # a repeat replaces

    store = _reload(monkeypatch, "file", db)           # a restart: memory is empty again
    assert store._alerts == []
    recent = store.list_recent()
    assert len(recent) == 2 and recent[0]["zone"] == "Mysuru City"
    assert [a["message"] for a in recent if a.get("watch_id")] == ["still tripped"]
    assert store.active_count() == 2

    store.clear()
    store = _reload(monkeypatch, "file", db)
    assert store.list_recent() == []
    _reload(monkeypatch, "memory", db)


def test_memory_mode_writes_nothing(tmp_path, monkeypatch):
    store = _reload(monkeypatch, "memory", tmp_path / "a.db")
    store.add_alert({"alert_type": "spike", "zone": "Udupi", "crime_type": "Theft"})
    assert not (tmp_path / "a.db").exists()
    store.clear()
