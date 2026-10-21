"""A conversation survives a restart: follow-ups and "why?" still have their context."""
import importlib


def test_a_session_survives_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTAR_SESSIONS", "file")
    monkeypatch.setenv("ANTAR_SESSIONS_DB", str(tmp_path / "s.db"))
    from app.core import sessions
    sessions = importlib.reload(sessions)
    sessions.append_user_turn("S1", "theft in Mysuru 2022", "en")
    sessions.append_assistant_turn("S1", "Mysuru City had 1,204 thefts.", "en", "T1", "R1",
                                   [{"agent": "query", "detail": "T1"}])
    sessions.update_session_entities("S1", {"zones": ["Mysuru City"]})

    sessions = importlib.reload(sessions)            # a restart: memory is empty again
    assert sessions._SESSIONS == {}
    assert [t["role"] for t in sessions.all_turns("S1")] == ["user", "assistant"]
    assert sessions.last_reasoning("S1") == [{"agent": "query", "detail": "T1"}]
    assert sessions.get_session_entities("S1")["zones"] == ["Mysuru City"]

    sessions.clear("S1")
    sessions = importlib.reload(sessions)
    assert sessions.all_turns("S1") == []


def test_memory_mode_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTAR_SESSIONS", "memory")
    monkeypatch.setenv("ANTAR_SESSIONS_DB", str(tmp_path / "s.db"))
    from app.core import sessions
    sessions = importlib.reload(sessions)
    sessions.append_user_turn("S2", "hello", "en")
    assert not (tmp_path / "s.db").exists()
