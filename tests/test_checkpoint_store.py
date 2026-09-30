"""
The durable case file (final_backend.md §6 P1-3).

The claim being tested is narrow and it is the whole point: **a thread survives the
process.** Everything else here exists because the checkpointer sits on the request path
of every chat turn, so a subtle break in it is a break in the product.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from app.agents.checkpoint_store import SqliteSaver, build_checkpointer

ROOT = Path(__file__).resolve().parent.parent


def _cfg(thread: str, ckpt_id: str | None = None) -> dict:
    c = {"thread_id": thread, "checkpoint_ns": ""}
    if ckpt_id:
        c["checkpoint_id"] = ckpt_id
    return {"configurable": c}


def _checkpoint(i: int) -> dict:
    # UUID6-shaped ids are time-ordered, and the store relies on that for "newest".
    return {"v": 4, "id": str(uuid.uuid1()), "ts": f"2026-09-25T00:00:{i:02d}+00:00",
            "channel_values": {"user_text": f"turn {i}"}, "channel_versions": {},
            "versions_seen": {}}


def test_put_then_get_roundtrips_the_state(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ck = _checkpoint(1)
    s.put(_cfg("T1"), ck, {"source": "loop", "step": 1}, {})

    got = s.get_tuple(_cfg("T1"))
    assert got is not None
    assert got.checkpoint["id"] == ck["id"]
    assert got.checkpoint["channel_values"]["user_text"] == "turn 1"
    assert got.metadata["step"] == 1


def test_get_returns_the_newest_checkpoint(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ids = []
    for i in range(1, 4):
        ck = _checkpoint(i)
        ids.append(ck["id"])
        s.put(_cfg("T1"), ck, {"source": "loop", "step": i}, {})
    assert s.get_tuple(_cfg("T1")).checkpoint["id"] == ids[-1]
    # …and an explicit id still addresses an older one, which is what time-travel needs.
    assert s.get_tuple(_cfg("T1", ids[0])).checkpoint["id"] == ids[0]


def test_threads_cannot_see_each_other(tmp_path):
    """Two officers' sessions are two threads. Leakage here is a confidentiality bug."""
    s = SqliteSaver(tmp_path / "cf.db")
    s.put(_cfg("officer-a"), _checkpoint(1), {"source": "loop", "step": 1}, {})
    s.put(_cfg("officer-b"), _checkpoint(2), {"source": "loop", "step": 1}, {})

    a = s.get_tuple(_cfg("officer-a")).checkpoint["channel_values"]["user_text"]
    b = s.get_tuple(_cfg("officer-b")).checkpoint["channel_values"]["user_text"]
    assert a == "turn 1" and b == "turn 2"
    assert len(list(s.list(_cfg("officer-a")))) == 1


def test_parent_config_chains_the_turns(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    first = _checkpoint(1)
    s.put(_cfg("T1"), first, {"source": "loop", "step": 1}, {})
    second = _checkpoint(2)
    s.put(_cfg("T1", first["id"]), second, {"source": "loop", "step": 2}, {})

    got = s.get_tuple(_cfg("T1"))
    assert got.parent_config["configurable"]["checkpoint_id"] == first["id"]


def test_pending_writes_come_back_with_the_checkpoint(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ck = _checkpoint(1)
    s.put(_cfg("T1"), ck, {"source": "loop", "step": 1}, {})
    s.put_writes(_cfg("T1", ck["id"]), [("results", {"query": {"rows": 3}})], "task-1")

    writes = s.get_tuple(_cfg("T1")).pending_writes
    assert len(writes) == 1
    task_id, channel, value = writes[0]
    assert (task_id, channel) == ("task-1", "results")
    assert value["query"]["rows"] == 3


def test_a_retried_task_overwrites_rather_than_duplicates(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ck = _checkpoint(1)
    s.put(_cfg("T1"), ck, {"source": "loop", "step": 1}, {})
    for attempt in (1, 2):
        s.put_writes(_cfg("T1", ck["id"]), [("results", {"attempt": attempt})], "task-1")
    writes = s.get_tuple(_cfg("T1")).pending_writes
    assert len(writes) == 1, "a retry must replace its previous write, not stack a second"
    assert writes[0][2]["attempt"] == 2


def test_list_is_newest_first_and_honours_before_and_limit(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ids = []
    for i in range(1, 6):
        ck = _checkpoint(i)
        ids.append(ck["id"])
        s.put(_cfg("T1"), ck, {"source": "loop", "step": i}, {})

    got = [t.checkpoint["id"] for t in s.list(_cfg("T1"))]
    assert got == list(reversed(ids))
    assert len(list(s.list(_cfg("T1"), limit=2))) == 2
    before = [t.checkpoint["id"] for t in s.list(_cfg("T1"), before=_cfg("T1", ids[2]))]
    assert before == list(reversed(ids[:2]))


def test_list_filters_on_metadata(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    s.put(_cfg("T1"), _checkpoint(1), {"source": "loop", "step": 1}, {})
    s.put(_cfg("T1"), _checkpoint(2), {"source": "input", "step": 2}, {})
    assert len(list(s.list(_cfg("T1"), filter={"source": "input"}))) == 1


def test_delete_thread_removes_its_writes_too(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db")
    ck = _checkpoint(1)
    s.put(_cfg("T1"), ck, {"source": "loop", "step": 1}, {})
    s.put_writes(_cfg("T1", ck["id"]), [("results", {"a": 1})], "task-1")
    s.delete_thread("T1")
    assert s.get_tuple(_cfg("T1")) is None
    with __import__("sqlite3").connect(str(s.path)) as con:
        assert con.execute("SELECT COUNT(*) FROM checkpoint_writes").fetchone()[0] == 0


def test_prune_drops_stale_threads_and_keeps_fresh_ones(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db", ttl_days=30)
    s.put(_cfg("old"), _checkpoint(1), {"source": "loop", "step": 1}, {})
    s.put(_cfg("new"), _checkpoint(2), {"source": "loop", "step": 1}, {})
    import sqlite3
    import time
    with sqlite3.connect(str(s.path)) as con:
        con.execute("UPDATE checkpoints SET created_at=? WHERE thread_id='old'",
                    (time.time() - 31 * 86400,))
    assert s.prune() == 1
    assert s.get_tuple(_cfg("old")) is None
    assert s.get_tuple(_cfg("new")) is not None


def test_ttl_zero_disables_pruning(tmp_path):
    s = SqliteSaver(tmp_path / "cf.db", ttl_days=0)
    s.put(_cfg("T1"), _checkpoint(1), {"source": "loop", "step": 1}, {})
    assert s.prune() == 0
    assert s.get_tuple(_cfg("T1")) is not None


def test_async_methods_mirror_the_sync_ones(tmp_path):
    """The graph is driven with ainvoke, so these are the paths that actually run."""
    import asyncio

    async def go():
        s = SqliteSaver(tmp_path / "cf.db")
        ck = _checkpoint(1)
        await s.aput(_cfg("T1"), ck, {"source": "loop", "step": 1}, {})
        await s.aput_writes(_cfg("T1", ck["id"]), [("results", {"a": 1})], "task-1")
        got = await s.aget_tuple(_cfg("T1"))
        assert got.checkpoint["id"] == ck["id"]
        assert [t.checkpoint["id"] async for t in s.alist(_cfg("T1"))] == [ck["id"]]
        await s.adelete_thread("T1")
        assert await s.aget_tuple(_cfg("T1")) is None

    asyncio.run(go())


def test_env_flag_restores_the_in_memory_saver(monkeypatch, tmp_path):
    """final_backend.md §2: every runtime swap stays a flag, with the old path intact."""
    # Compare against the imported class, not its name: in langgraph 0.6 `MemorySaver` is
    # an alias for `InMemorySaver`, so a name check asserts the alias rather than the type.
    from langgraph.checkpoint.memory import MemorySaver
    monkeypatch.setenv("ANTAR_CHECKPOINT", "memory")
    assert isinstance(build_checkpointer(), MemorySaver)
    monkeypatch.setenv("ANTAR_CHECKPOINT", "sqlite")
    monkeypatch.setenv("ANTAR_CHECKPOINT_DB", str(tmp_path / "cf.db"))
    assert isinstance(build_checkpointer(), SqliteSaver)


def test_thread_survives_a_real_process_restart(tmp_path):
    """The claim P1-3 exists to make, tested the only way it can honestly be tested.

    Same-process reads prove nothing about durability — an in-memory dict passes those.
    This writes a checkpoint in one interpreter, lets it EXIT, and reads it back from a
    second one. That is what "an officer's thread survives a redeploy" means.
    """
    db = tmp_path / "cf.db"
    write = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "from app.agents.checkpoint_store import SqliteSaver\n"
        "s = SqliteSaver(r'%s')\n"
        "s.put({'configurable': {'thread_id': 'T1', 'checkpoint_ns': ''}},\n"
        "      {'v': 4, 'id': 'ckpt-restart', 'ts': '2026-09-25T00:00:00+00:00',\n"
        "       'channel_values': {'user_text': 'who is the most connected accused?'},\n"
        "       'channel_versions': {}, 'versions_seen': {}},\n"
        "      {'source': 'loop', 'step': 1}, {})\n"
    ) % (ROOT, db)
    r = subprocess.run([sys.executable, "-c", write], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]

    # A brand-new saver object in THIS process — the writer is gone.
    s = SqliteSaver(db)
    got = s.get_tuple(_cfg("T1"))
    assert got is not None, "the thread did not survive the process — P1-3 is not done"
    assert got.checkpoint["id"] == "ckpt-restart"
    assert got.checkpoint["channel_values"]["user_text"] == \
        "who is the most connected accused?"


# ── surviving a corrupt case file ────────────────────────────────────────────
# A durable case file that can break every request is WORSE than the in-memory saver it
# replaced. This is not hypothetical: leaked connections let concurrent writers corrupt
# the store, after which every turn raised
# `sqlite3.DatabaseError: database disk image is malformed` and the chat API 500'd.

def test_a_corrupt_case_file_is_quarantined_not_fatal(tmp_path):
    db = tmp_path / "cf.db"
    db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 600)     # header, then garbage

    s = SqliteSaver(db)                       # must not raise
    s.put(_cfg("T1"), _checkpoint(1), {"source": "loop", "step": 1}, {})
    assert s.get_tuple(_cfg("T1")) is not None, "a fresh store must work after quarantine"

    kept = list(tmp_path.glob("cf.corrupt-*.db"))
    assert kept, "the corrupt file is evidence — it is preserved, not deleted"


def test_a_healthy_case_file_is_never_quarantined(tmp_path):
    db = tmp_path / "cf.db"
    s = SqliteSaver(db)
    s.put(_cfg("T1"), _checkpoint(1), {"source": "loop", "step": 1}, {})

    again = SqliteSaver(db)                   # reopen
    assert again.get_tuple(_cfg("T1")) is not None, "a good store must survive reopening"
    assert not list(tmp_path.glob("cf.corrupt-*.db"))


def test_an_unreadable_store_loses_the_thread_not_the_turn(tmp_path, monkeypatch):
    """get_tuple degrades to 'new conversation' instead of raising into the request."""
    import sqlite3 as _sq
    s = SqliteSaver(tmp_path / "cf.db")
    s.put(_cfg("T1"), _checkpoint(1), {"source": "loop", "step": 1}, {})

    def boom(*_a, **_k):
        raise _sq.DatabaseError("database disk image is malformed")

    monkeypatch.setattr(s, "_get_tuple", boom)
    assert s.get_tuple(_cfg("T1")) is None, "an unreadable store must not raise at callers"


def test_connections_do_not_leak(tmp_path):
    """`with sqlite3.connect(...)` commits but does NOT close — the leak that started this.

    Writing many checkpoints must not accumulate open handles; if it does, the store
    eventually reports 'database is locked' under the graph's fan-out.
    """
    import gc
    import sqlite3 as _sq
    s = SqliteSaver(tmp_path / "cf.db")
    for i in range(40):
        s.put(_cfg(f"T{i}"), _checkpoint(i), {"source": "loop", "step": i}, {})
    gc.collect()
    open_conns = [o for o in gc.get_objects() if isinstance(o, _sq.Connection)]
    assert len(open_conns) < 5, f"{len(open_conns)} sqlite connections still alive"
