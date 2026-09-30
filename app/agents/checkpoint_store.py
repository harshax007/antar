"""
Antar — a durable case file for the agent graph (final_backend.md §6 P1-3).

The graph shipped with LangGraph's `MemorySaver`: an in-process dict. Every turn's state
lived in RAM and died with the process, so an officer's thread did not survive a restart,
a redeploy or a crash. `AGENTS.md` listed it under "Known gaps" — *"Session continuity
resets on restart; there is no durable case file"* — and for police work that is not a
nice-to-have. An investigator who asks four follow-up questions, gets paged, and comes back
after the container recycled should find the thread where they left it.

This is a `BaseCheckpointSaver` over stdlib `sqlite3`.

**Why not `langgraph-checkpoint-sqlite`?** It would be one more dependency in an image
that has to fit 2 GB, and it puts retention — how long an officer's questions are kept —
inside a third-party package. Under the DPDP Act 2023 that is a decision Antar should own
and be able to point at (`prune()` below). The interface is four sync methods and their
async twins; the storage is two tables. That trade is worth making here and it is not a
trade worth making often.

**Concurrency.** A connection is opened per call rather than shared. `sqlite3` objects are
thread-affine by default, and the graph runs nodes in a thread pool, so a shared handle
would need `check_same_thread=False` plus a lock that serialises every node. WAL mode plus
short-lived connections lets readers and the writer proceed together, which is what a
fan-out of eight nodes writing their updates actually does.

Switch back at any time with `ANTAR_CHECKPOINT=memory` — the old path is intact, per the
non-negotiables in final_backend.md §2.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import threading
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

__all__ = ["SqliteSaver", "checkpoint_db_path", "build_checkpointer"]

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_id     TEXT,
    type          TEXT,
    checkpoint    BLOB NOT NULL,
    metadata_type TEXT,
    metadata      BLOB NOT NULL,
    created_at    REAL NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Every read is "the newest checkpoint for this thread", so the index has to descend on
-- checkpoint_id. LangGraph ids are UUID6 — time-ordered — so lexical DESC is chronological.
CREATE INDEX IF NOT EXISTS ix_ckpt_thread
    ON checkpoints(thread_id, checkpoint_ns, checkpoint_id DESC);
CREATE INDEX IF NOT EXISTS ix_ckpt_created ON checkpoints(created_at);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id       TEXT NOT NULL,
    task_path     TEXT NOT NULL DEFAULT '',
    idx           INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    type          TEXT,
    value         BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
"""

# Retention. A case file is not a permanent record of every question ever asked, and an
# unbounded checkpoint table is both a disk problem in a 2 GB box and a data-minimisation
# problem under the DPDP Act. Threads untouched for this long are pruned on startup.
DEFAULT_TTL_DAYS = 30

_init_lock = threading.Lock()
_initialised: set[str] = set()


def checkpoint_db_path() -> Path:
    """Where the case file lives. `ANTAR_CHECKPOINT_DB` overrides.

    Defaults beside the observability store rather than next to `main.db`: this is
    operational state, not part of the FIR registry, and it must never end up inside a
    database that gets shipped as a dataset.
    """
    override = os.getenv("ANTAR_CHECKPOINT_DB")
    if override:
        return Path(override)
    from app.obs.config import OBS_DIR
    return Path(OBS_DIR) / "case_file.db"


@contextmanager
def _connect(path: Path):
    """A connection that is committed AND CLOSED.

    This was `with sqlite3.connect(...) as con:` at eight call sites, which is a trap
    `sqlite3` sets deliberately: its context manager commits or rolls back the
    transaction, and does **not** close the connection. Every read and every write leaked
    an open handle holding its lock, so a multi-turn conversation walked into
    `sqlite3.OperationalError: database is locked` — the graph fans out to eight nodes and
    each one writes.

    Wrapping it here rather than fixing eight `with` blocks means the mistake cannot come
    back at a ninth call site.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30.0)
    try:
        con.execute("PRAGMA busy_timeout=30000;")
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _warn(msg: str) -> None:
    """Print a warning that cannot itself raise.

    The first version of the quarantine path used an emoji, and on a cp1252 console the
    print raised UnicodeEncodeError *inside* the recovery routine — so the code whose only
    job is to stop a corrupt file breaking things became the thing that broke. ASCII only,
    and swallowed if even that fails: a warning is never worth an exception.
    """
    try:
        print(f"  [case-file] {msg}")
    except Exception:                       # noqa: BLE001
        pass


def _quarantine_if_corrupt(path: Path) -> bool:
    """Move a corrupt case file aside and start a fresh one. True if quarantined.

    A durable case file that can break every request is WORSE than the in-memory saver it
    replaced. This was not hypothetical: leaked connections (see `_connect`) let concurrent
    writers corrupt the store, after which `get_tuple` raised
    `sqlite3.DatabaseError: database disk image is malformed` on every turn and the chat
    API returned 500s. The thread history was already unreadable at that point; refusing to
    serve anything as well just turns a lost conversation into a lost product.

    Checkpoints are disposable by design — they carry a 30-day TTL and rebuild from the
    next turn — so the safe move is to preserve the evidence and continue. The corrupt file
    is kept, not deleted: it is the only record of how it broke.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        con = sqlite3.connect(str(path), timeout=5.0)
        try:
            # quick_check(1) stops at the first problem instead of walking every page of a
            # large file, which is all we need to decide.
            ok = str(con.execute("PRAGMA quick_check(1)").fetchone()[0]).lower() == "ok"
        finally:
            con.close()
    except sqlite3.DatabaseError:
        ok = False
    if ok:
        return False

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dead = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
    try:
        path.replace(dead)
        for suffix in ("-wal", "-shm"):
            side = Path(str(path) + suffix)
            if side.exists():
                side.unlink()
        _warn(f"was corrupt - quarantined to {dead.name}; starting a fresh one. "
              "Earlier threads are not recoverable.")
    except OSError as exc:
        _warn(f"is corrupt and could not be quarantined ({exc})")
        return False
    return True


def _ensure_schema(path: Path) -> None:
    key = str(path)
    if key in _initialised:
        return
    with _init_lock:
        if key in _initialised:
            return
        with _connect(path) as con:
            con.executescript(_SCHEMA)
        _initialised.add(key)


def _cfg(config: dict | None) -> tuple[str, str, str | None]:
    c = (config or {}).get("configurable", {}) or {}
    return str(c.get("thread_id", "")), str(c.get("checkpoint_ns", "") or ""), get_checkpoint_id(config or {})


class SqliteSaver(BaseCheckpointSaver):
    """Durable checkpointer. `thread_id` is the session id, exactly as before."""

    def __init__(self, path: Path | str | None = None, *, ttl_days: int = DEFAULT_TTL_DAYS):
        super().__init__()
        self.path = Path(path) if path else checkpoint_db_path()
        self.ttl_days = ttl_days
        _quarantine_if_corrupt(self.path)
        _ensure_schema(self.path)

    # ── writes ────────────────────────────────────────────────────────────────
    def put(self, config, checkpoint: Checkpoint, metadata: CheckpointMetadata,
            new_versions: ChannelVersions):
        thread_id, ns, _ = _cfg(config)
        parent_id = (config.get("configurable") or {}).get("checkpoint_id")
        ctype, cblob = self.serde.dumps_typed(checkpoint)
        # The metadata's serialisation TYPE is stored too. Assuming "json" on the way back
        # is a bug waiting for the day the serde picks msgpack for a dict that happens to
        # hold bytes — it would raise on read, i.e. exactly when an officer reopens a
        # thread. Round-trip what was actually written.
        mtype, mblob = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        with _connect(self.path) as con:
            con.execute(
                "INSERT OR REPLACE INTO checkpoints "
                "(thread_id, checkpoint_ns, checkpoint_id, parent_id, type, checkpoint,"
                " metadata_type, metadata, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (thread_id, ns, checkpoint["id"], parent_id, ctype, cblob,
                 mtype, mblob, time.time()),
            )
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns,
                                 "checkpoint_id": checkpoint["id"]}}

    def put_writes(self, config, writes: Sequence[tuple[str, Any]], task_id: str,
                   task_path: str = "") -> None:
        thread_id, ns, ckpt_id = _cfg(config)
        rows = []
        for idx, (channel, value) in enumerate(writes):
            vtype, vblob = self.serde.dumps_typed(value)
            # Special channels (ERROR, INTERRUPT, RESUME, SCHEDULED) have reserved slots so
            # a retry overwrites the previous attempt instead of appending a duplicate.
            rows.append((thread_id, ns, ckpt_id or "", task_id, task_path,
                         WRITES_IDX_MAP.get(channel, idx), channel, vtype, vblob))
        if not rows:
            return
        with _connect(self.path) as con:
            con.executemany(
                "INSERT OR REPLACE INTO checkpoint_writes "
                "(thread_id, checkpoint_ns, checkpoint_id, task_id, task_path, idx,"
                " channel, type, value) VALUES (?,?,?,?,?,?,?,?,?)", rows)

    # ── reads ─────────────────────────────────────────────────────────────────
    def _pending_writes(self, con, thread_id: str, ns: str, ckpt_id: str) -> list:
        cur = con.execute(
            "SELECT task_id, channel, type, value FROM checkpoint_writes "
            "WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=? ORDER BY task_id, idx",
            (thread_id, ns, ckpt_id))
        return [(r[0], r[1], self.serde.loads_typed((r[2], r[3]))) for r in cur.fetchall()]

    def _row_to_tuple(self, con, row) -> CheckpointTuple:
        thread_id, ns, ckpt_id, parent_id, ctype, cblob, mtype, mblob = row
        cfg = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns,
                                "checkpoint_id": ckpt_id}}
        parent = ({"configurable": {"thread_id": thread_id, "checkpoint_ns": ns,
                                    "checkpoint_id": parent_id}} if parent_id else None)
        return CheckpointTuple(
            config=cfg,
            checkpoint=self.serde.loads_typed((ctype, cblob)),
            metadata=self.serde.loads_typed((mtype or "json", mblob)),
            parent_config=parent,
            pending_writes=self._pending_writes(con, thread_id, ns, ckpt_id),
        )

    _COLS = ("thread_id, checkpoint_ns, checkpoint_id, parent_id, type, checkpoint, "
             "metadata_type, metadata")

    def get_tuple(self, config) -> CheckpointTuple | None:
        thread_id, ns, ckpt_id = _cfg(config)
        if not thread_id:
            return None
        try:
            return self._get_tuple(config, thread_id, ns, ckpt_id)
        except sqlite3.DatabaseError as exc:
            # An unreadable store means the thread is lost, not that the turn must fail.
            # Returning None makes this look like a brand-new conversation, which is
            # exactly what it now is.
            _warn(f"unreadable ({exc}); this turn starts a fresh thread")
            return None

    def _get_tuple(self, config, thread_id: str, ns: str,
                   ckpt_id: str | None) -> CheckpointTuple | None:
        with _connect(self.path) as con:
            if ckpt_id:
                cur = con.execute(
                    f"SELECT {self._COLS} FROM checkpoints "
                    "WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                    (thread_id, ns, ckpt_id))
            else:
                cur = con.execute(
                    f"SELECT {self._COLS} FROM checkpoints "
                    "WHERE thread_id=? AND checkpoint_ns=? ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id, ns))
            row = cur.fetchone()
            return self._row_to_tuple(con, row) if row else None

    def list(self, config, *, filter: dict[str, Any] | None = None,
             before=None, limit: int | None = None) -> Iterator[CheckpointTuple]:
        where, params = [], []
        if config:
            thread_id, ns, _ = _cfg(config)
            if thread_id:
                where.append("thread_id=?"); params.append(thread_id)
                where.append("checkpoint_ns=?"); params.append(ns)
        if before:
            bid = get_checkpoint_id(before)
            if bid:
                where.append("checkpoint_id < ?"); params.append(bid)
        sql = f"SELECT {self._COLS} FROM checkpoints"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY checkpoint_id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        with _connect(self.path) as con:
            rows = con.execute(sql, params).fetchall()
            for row in rows:
                t = self._row_to_tuple(con, row)
                # `filter` matches on metadata, which is a blob in SQL — checked in Python
                # rather than pushed into the query, because a JSON path over a serialised
                # column would silently miss any non-JSON serialisation the serde chooses.
                if filter and not all((t.metadata or {}).get(k) == v for k, v in filter.items()):
                    continue
                yield t

    def delete_thread(self, thread_id: str) -> None:
        with _connect(self.path) as con:
            con.execute("DELETE FROM checkpoints WHERE thread_id=?", (thread_id,))
            con.execute("DELETE FROM checkpoint_writes WHERE thread_id=?", (thread_id,))

    # ── async twins ───────────────────────────────────────────────────────────
    # The graph is driven with `ainvoke`, so these are the methods that actually run.
    # SQLite has no async driver in the stdlib; a worker thread is the honest way to keep
    # the event loop free, and each call opens its own connection so that is safe.
    async def aget_tuple(self, config) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(self, config, *, filter=None, before=None,
                    limit=None) -> AsyncIterator[CheckpointTuple]:
        items = await asyncio.to_thread(
            lambda: list(self.list(config, filter=filter, before=before, limit=limit)))
        for it in items:
            yield it

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id: str, task_path: str = "") -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)

    # ── retention ─────────────────────────────────────────────────────────────
    def prune(self, ttl_days: int | None = None) -> int:
        """Drop threads untouched for longer than the TTL. Returns rows removed."""
        days = self.ttl_days if ttl_days is None else ttl_days
        if days <= 0:
            return 0
        cutoff = time.time() - days * 86400
        with _connect(self.path) as con:
            stale = [r[0] for r in con.execute(
                "SELECT thread_id FROM checkpoints GROUP BY thread_id "
                "HAVING MAX(created_at) < ?", (cutoff,)).fetchall()]
            if not stale:
                return 0
            marks = ",".join("?" * len(stale))
            n = con.execute(f"DELETE FROM checkpoints WHERE thread_id IN ({marks})",
                            stale).rowcount
            con.execute(f"DELETE FROM checkpoint_writes WHERE thread_id IN ({marks})", stale)
        return n

    def stats(self) -> dict:
        with _connect(self.path) as con:
            threads, ckpts = con.execute(
                "SELECT COUNT(DISTINCT thread_id), COUNT(*) FROM checkpoints").fetchone()
        size = self.path.stat().st_size if self.path.exists() else 0
        return {"backend": "sqlite", "path": str(self.path), "threads": threads,
                "checkpoints": ckpts, "mb": round(size / 1048576, 2)}


def build_checkpointer():
    """The checkpointer `build_graph` uses.

    Durable by default. `ANTAR_CHECKPOINT=memory` restores the old in-process saver, and a
    store that cannot be opened at all falls back to it with a loud warning rather than
    refusing to start: a backend that will not boot is worse than one that has forgotten
    yesterday's threads.
    """
    mode = (os.getenv("ANTAR_CHECKPOINT") or "sqlite").strip().lower()
    if mode == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    try:
        saver = SqliteSaver()
        try:
            removed = saver.prune()
            if removed:
                _warn(f"pruned {removed} checkpoint(s) past the "
                      f"{saver.ttl_days}-day retention")
        except Exception:                       # noqa: BLE001 — never block boot on retention
            pass
        return saver
    except Exception as exc:                    # noqa: BLE001
        _warn(f"unavailable ({exc}); using the in-memory checkpointer")
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
