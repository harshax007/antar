"""
Antar — the single source of truth for the database location.

The product ships ONE database: `main.db`, built to the official Karnataka Police FIR ER
schema with a `FIRs` compatibility table layered on top so existing callers keep working
unchanged.

Override with the ANTAR_DB environment variable (used by tests and by the Catalyst
deployment, which mounts the database at a different path).
"""
import gzip
import os
import shutil
import tempfile
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))

DEFAULT_DB_NAME = "main.db"
DEFAULT_DB_PATH = os.path.join(_BACKEND_ROOT, DEFAULT_DB_NAME)

def _db_from_env_file() -> str | None:
    """Read ANTAR_DB out of .env, if it is set there.

    This module is imported long before anything calls load_dotenv() — run.py only does
    so after `from main import app` — and it reads os.environ directly, so a developer
    who points ANTAR_DB at another database in .env would otherwise be silently ignored
    and keep using the default file. Only this one key is read: loading the whole .env
    into os.environ here would change what every other module sees at import time.

    A real environment variable still wins (Catalyst and Docker set one).
    """
    path = os.path.join(_BACKEND_ROOT, ".env")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("ANTAR_DB"):
                    continue
                key, _, value = line.partition("=")
                if key.strip() != "ANTAR_DB":
                    continue
                value = value.split("#", 1)[0].strip().strip('"').strip("'")
                return value or None
    except OSError:
        pass
    return None


_env_db = os.environ.get("ANTAR_DB") or _db_from_env_file() or DEFAULT_DB_NAME

# If ANTAR_DB is an absolute path, use it. Otherwise, assume it's in the root.
if os.path.isabs(_env_db):
    _source_db = _env_db
else:
    _source_db = os.path.join(_BACKEND_ROOT, _env_db)

# Catalyst AppSail runs on a read-only filesystem, so the database has to live under
# /tmp for SQLite to be able to create its journal. To keep the deploy package small we
# ship main.db.gz (~46 MB vs 276 MB) and expand it on the first cold start.
_ON_CATALYST = bool(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT"))

if _ON_CATALYST:
    DB_PATH = os.path.join(tempfile.gettempdir(), os.path.basename(_source_db))
else:
    DB_PATH = _source_db

_stage_lock = threading.Lock()
_staged = not _ON_CATALYST          # local runs use the file in place — nothing to stage


_wal_checked = False


def _ensure_wal(path: str) -> None:
    """Put the database in WAL mode (persistent; a no-op once set).

    main.db.gz is a data-only snapshot in rollback-journal mode. In that mode a reader is
    refused ("database is locked") whenever the startup warm-up holds a write lock, so
    page loads failed with 500s for the first minutes after every deploy. Under WAL,
    readers never block on the writer. Best effort: if another connection holds the
    database right now, the next start sets it.
    """
    global _wal_checked
    if _wal_checked or not os.path.exists(path):
        return
    _wal_checked = True
    try:
        import sqlite3
        con = sqlite3.connect(path, timeout=30)
        try:
            mode = con.execute("PRAGMA journal_mode").fetchone()[0]
            if str(mode).lower() != "wal":
                mode = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                print(f"[db_path] journal_mode -> {mode}")
        finally:
            con.close()
    except Exception as e:                                  # never block startup on this
        print(f"[db_path] could not enable WAL: {e}")


def _is_registry(path: str) -> bool:
    """True when `path` is a database that holds the FIR registry, not just a file."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        import sqlite3
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        try:
            return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'FIRs'").fetchone() is not None
        finally:
            con.close()
    except Exception:
        return False


# The Brain's corpus index ships beside the registry and is looked for beside the staged
# one (app/second_brain/vec_store.py). Without this copy a deployed container searched an
# empty index: 0 of 100,000 FIRs.
_SIDECARS = ("brain_vectors.db", "brain_vectors.i8", "brain_vectors.ids", "brain_vectors.mult")


def _stage_sidecars() -> None:
    src_dir, dst_dir = os.path.dirname(_source_db), os.path.dirname(DB_PATH)
    if os.path.abspath(src_dir) == os.path.abspath(dst_dir):
        return
    for name in _SIDECARS:
        src, dst = os.path.join(src_dir, name), os.path.join(dst_dir, name)
        try:
            if not os.path.exists(src):
                continue
            if os.path.exists(dst) and os.path.getsize(dst) >= os.path.getsize(src):
                continue                     # already staged (the store only grows)
            tmp = f"{dst}.staging-{os.getpid()}"
            shutil.copyfile(src, tmp)
            for stale in (dst + "-wal", dst + "-shm"):
                if os.path.exists(stale):
                    os.remove(stale)
            os.replace(tmp, dst)
            print(f"[db_path] staged {name} ({os.path.getsize(dst) / 1048576:.0f} MB)")
        except Exception as e:               # the Brain degrades; the registry still serves
            print(f"[db_path] could not stage {name}: {e}")


def ensure_db_staged() -> str:
    """Expand main.db.gz into /tmp if it is not there yet. Idempotent and thread-safe.

    Called from the startup warmup and from get_db_path(). This work used to run at
    MODULE IMPORT time, which meant ~276 MB of gzip inflation happened before uvicorn
    could bind its port — the container looked dead for the whole of it, and every
    request in that window (including the health probe) queued behind it.

    Two concurrent first-requests used to be able to race here as well, each writing the
    same target path; the lock plus the write-to-temp-then-rename below make a partially
    written database impossible to observe.
    """
    global _staged
    if _staged:
        if not _wal_checked:
            _ensure_wal(DB_PATH)
        return DB_PATH
    with _stage_lock:
        if _staged:                     # another thread won the race
            return DB_PATH
        if _is_registry(DB_PATH):
            _staged = True
            _stage_sidecars()
            return DB_PATH
        # A file that is there but is not the registry was created by a connection that
        # opened the path before staging (sqlite creates on connect). Treating it as
        # staged left a deployed container running on an empty database. Replace it, and
        # its journal files with it: a stale -wal beside a new database corrupts it.
        for stale in (DB_PATH, DB_PATH + "-wal", DB_PATH + "-shm"):
            try:
                if os.path.exists(stale):
                    os.remove(stale)
                    print(f"[db_path] removed pre-staging file {os.path.basename(stale)}")
            except OSError as e:
                print(f"[db_path] could not remove {stale}: {e}")

        gz_src = _source_db + ".gz"
        tmp_out = f"{DB_PATH}.staging-{os.getpid()}"
        t0 = time.time()
        try:
            if os.path.exists(gz_src):
                print(f"[db_path] staging {gz_src} -> {DB_PATH}")
                # 8 MB chunks: the copyfileobj default is 64 KB, which costs thousands of
                # extra syscalls inflating a file this size.
                with gzip.open(gz_src, "rb") as f_in, open(tmp_out, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out, length=8 * 1024 * 1024)
            elif os.path.exists(_source_db):
                print(f"[db_path] staging {_source_db} -> {DB_PATH}")
                shutil.copyfile(_source_db, tmp_out)
            else:
                print(f"[db_path] no database found at {_source_db} or {gz_src}")
                return DB_PATH
            os.replace(tmp_out, DB_PATH)          # atomic within the same filesystem
            print(f"[db_path] database ready in {time.time() - t0:.1f}s "
                  f"({os.path.getsize(DB_PATH) / 1048576:.0f} MB)")
            _staged = True
            _ensure_wal(DB_PATH)
            _stage_sidecars()
        except Exception as e:
            print(f"[db_path] Failed to stage DB: {e}")
            try:
                if os.path.exists(tmp_out):
                    os.remove(tmp_out)
            except OSError:
                pass
    return DB_PATH


def get_db_path() -> str:
    """Resolve the DB path at call time, staging it first if necessary."""
    return ensure_db_staged()


# ── Connections to the registry ──────────────────────────────────────────────
# Every module opens its own short-lived connection, so SQLite's page cache starts empty
# each time. Memory-mapping the file lets reads come straight from the OS page cache, which
# stays warm between connections. Measured on the 10-lakh registry (1.5 GB): a district-year
# breakdown 34 ms -> 11 ms, one FIR by id 2 ms -> 0.3 ms. Reads only; writes are unchanged.
_MMAP_BYTES = 2 * 1024 ** 3


class RegistryConnection(__import__("sqlite3").Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.execute(f"PRAGMA mmap_size={_MMAP_BYTES}")
            self.execute("PRAGMA cache_size=-32768")         # 32 MB, allocated only as used
            self.execute("PRAGMA temp_store=MEMORY")
        except Exception:                                      # a tuning miss never fails a query
            pass


def registry_connect(*args, **kwargs):
    """sqlite3.connect with the read tuning above; same arguments."""
    import sqlite3
    kwargs.setdefault("factory", RegistryConnection)
    return sqlite3.connect(*args, **kwargs)
