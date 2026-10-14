"""Speed and visibility fixes of 2026-10-14: the Map's Gi* centre points are not recomputed
over a million rows on every call, the Data Overview survives a restart, large responses are
compressed (the chat stream is not), and a count of demonstration records is said beside the
bottom line rather than folded under Limits."""
import sqlite3

import pytest

from app.services import product_store as PS


# ── Data Overview kept on disk, tied to the registry ─────────────────────────
@pytest.fixture
def disk(tmp_path, monkeypatch):
    db = str(tmp_path / "p.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE FIRs (x)")
    c.executemany("INSERT INTO FIRs VALUES (?)", [(i,) for i in range(5)])
    c.commit()
    c.close()
    import app.core.db_path as dbp
    monkeypatch.setattr(dbp, "get_db_path", lambda: db)
    monkeypatch.setattr(PS, "_products", {})
    monkeypatch.setattr(PS, "_expires_at", {})
    monkeypatch.setitem(PS._sig_cache, "value", None)
    return db


def _restart():
    PS._products.clear()
    PS._expires_at.clear()
    PS._sig_cache["value"] = None


def test_a_dataset_product_is_served_after_a_restart(disk):
    PS.put_product("dataset:overview:v2", {"total": 5, "by": [1, 2]}, ttl=600)
    _restart()
    assert PS.get_product("dataset:overview:v2") == {"total": 5, "by": [1, 2]}


def test_new_rows_make_the_disk_copy_stale(disk):
    PS.put_product("dataset:overview:v2", {"total": 5}, ttl=600)
    c = sqlite3.connect(disk)
    c.execute("INSERT INTO FIRs VALUES (99)")
    c.commit()
    c.close()
    _restart()
    assert PS.get_product("dataset:overview:v2") is None


def test_an_expired_disk_copy_is_not_served(disk, monkeypatch):
    PS.put_product("dataset:overview:v2", {"total": 5}, ttl=600)
    _restart()
    import time
    monkeypatch.setattr(time, "time", lambda: 10 ** 12)
    assert PS.get_product("dataset:overview:v2") is None


def test_only_dataset_products_go_to_disk_and_odd_types_never_do(disk):
    PS.put_product("briefing:shift:all", {"x": 1}, ttl=600)
    PS.put_product("dataset:odd", {"t": (1, 2)}, ttl=600)          # a tuple would come back a list
    _restart()
    assert PS.get_product("briefing:shift:all") is None and PS.get_product("dataset:odd") is None


def test_invalidating_clears_the_disk_copy(disk):
    PS.put_product("dataset:overview:v2", {"total": 5}, ttl=600)
    PS.invalidate("dataset:")
    _restart()
    assert PS.get_product("dataset:overview:v2") is None


# ── Gi* centre points ─────────────────────────────────────────────────────────
def test_centre_points_are_recomputed_only_when_rows_are_added(tmp_path, monkeypatch):
    from app.services import anomaly as A
    db = str(tmp_path / "a.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE FIRs (zone, lat, lon)")
    c.execute("CREATE VIEW crimes AS SELECT zone, lat, lon FROM FIRs")
    c.executemany("INSERT INTO FIRs VALUES (?, ?, ?)", [("A", 12.0, 77.0), ("A", 14.0, 77.0), ("B", 15.0, 75.0)])
    c.commit()
    monkeypatch.setattr(A, "DB_PATH", db)
    monkeypatch.setattr(A, "_centroid_cache", {"sig": None, "value": {}})
    assert A._zone_centroids()["A"] == (13.0, 77.0)
    c.execute("UPDATE FIRs SET lat = 99 WHERE zone = 'B'")          # same newest row: served from cache
    c.commit()
    assert A._zone_centroids()["B"] == (15.0, 75.0)
    c.execute("INSERT INTO FIRs VALUES ('C', 16.0, 76.0)")
    c.commit()
    c.close()
    got = A._zone_centroids()
    assert set(got) == {"A", "B", "C"} and got["B"] == (99.0, 75.0)


# ── compression ──────────────────────────────────────────────────────────────
def _app():
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse, StreamingResponse
    import main
    a = FastAPI()

    @a.get("/api/big")
    def big():
        return PlainTextResponse("x" * 5000)

    @a.get("/api/chat/stream")
    def stream():
        return StreamingResponse(iter(["data: a\n\n", "data: b\n\n"]), media_type="text/event-stream")
    a.add_middleware(main._Compress, minimum_size=1024)
    return a


def test_large_responses_are_compressed_and_the_chat_stream_is_not():
    from fastapi.testclient import TestClient
    c = TestClient(_app())
    assert c.get("/api/big", headers={"Accept-Encoding": "gzip"}).headers.get("content-encoding") == "gzip"
    r = c.get("/api/chat/stream", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in r.headers and r.text == "data: a\n\ndata: b\n\n"


# ── demonstration records said beside the bottom line ────────────────────────
def test_a_demonstration_count_is_context_not_a_folded_limit():
    from app.core.antar_identity import present
    answer = ("[COMPUTED] **Bengaluru City** has the most vehicle theft cases - **175** FIRs.\n"
              "• Note: the real KSP register has no separate head for vehicle theft. These are demonstration "
              "records, not registered FIRs; the register files such cases under a broader head such as Theft.\n"
              "• Note: Oct 2026 is still in progress.\n"
              "Top 6 districts:\n1. Bengaluru City - 175 (70%)")
    s = present(answer, {}, "en")["sections"]
    assert s["context"][0].startswith("The real KSP register has no separate head")
    assert not any("demonstration" in l for l in s["limits"])
    assert any("still in progress" in l for l in s["limits"])
