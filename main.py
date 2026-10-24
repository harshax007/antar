"""
Antar — FastAPI Backend Entry Point
Datathon 2026 | Python 3.12 + FastAPI + LangGraph + Second Brain
"""

import sys

# Windows consoles default to cp1252 → emoji/Kannada in startup logs crash uvicorn.
# Force UTF-8 so console output is safe on every platform.
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Second Brain models (BGE embedder + CrossEncoder reranker) run OFFLINE-FIRST:
# force Hugging Face into local-cache mode BEFORE any transformers/huggingface_hub
# import evaluates its offline constant, so no startup HEAD request ever hangs on
# a missing network. Set ANTAR_BRAIN_ONLINE=1 to permit a one-time download.
import os
if os.getenv("ANTAR_BRAIN_ONLINE") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# numpy and scipy each bundle their own OpenBLAS, and OpenBLAS reserves a workspace per
# CPU thread the first time it is imported. Measured on a 12-core machine (2026-09-22,
# docs/footprint/blas-threads.md): importing numpy + scipy commits 758 MB of private
# memory at the default thread count and 20 MB at one thread, while the forecast fit
# slows by ~1.6% and warm query latency does not move. The deployed image already sets
# OMP_NUM_THREADS=1 (Dockerfile, app-config.json) — OpenBLAS falls back to that variable
# when its own is unset — so pinning it here only makes a local run, a test run and a
# deploy whose env var went missing behave the same way the container already does.
# All three are set together, and only when the operator set NONE of them. Per-variable
# setdefault would break the documented precedence (OPENBLAS_NUM_THREADS beats
# OMP_NUM_THREADS): someone raising OMP_NUM_THREADS to 3 would still get a 1-thread
# OpenBLAS, because this code would have pinned its variable. Caught by
# tests/test_runtime_env.py::test_operator_override_wins.
# This must run BEFORE anything imports numpy, hence its position next to the HF block.
# Deliberately NOT applied to the offline CLI tools (python -m app.forecast.run /
# .backtest): a batch refit is allowed to use every core it can get.
_BLAS_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
if not any(os.environ.get(_v) for _v in _BLAS_VARS):
    for _v in _BLAS_VARS:
        os.environ[_v] = "1"

# onnxruntime's native module must be loaded BEFORE scikit-learn's, or the process dies.
#
# Measured 2026-09-24 on a clean torch-free venv (Windows, Python 3.11.15,
# scikit-learn 1.4.1.post1 + onnxruntime 1.30.0):
#
#     import sklearn; import onnxruntime   ->  Windows fatal exception: access violation
#     import onnxruntime; import sklearn   ->  fine
#
# Both wheels ship their own OpenMP runtime. When scikit-learn's loads first,
# onnxruntime's `capi/_pybind_state` import hits an access violation inside
# `create_module` and the interpreter is killed outright — no traceback, exit 139,
# nothing in the log after "Loading Second Brain embedder". The server reached
# "Application startup complete" and then vanished mid-warm-up.
#
# It was invisible until now only because a torch-bearing environment loads a compatible
# OpenMP first and wins the race. `Dockerfile.onnx` installs no torch, so the deployed
# runtime image is exactly the configuration that crashes. Pinning the order here is the
# fix that holds in both.
#
# Guarded: a torch-only environment has no onnxruntime and must still boot.
try:
    import onnxruntime as _onnxruntime  # noqa: F401
except Exception:
    pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.core.auth_middleware import require_role, resolve_identity, install_gateway
from app.core import security
from app.services import audit_store
from app.second_brain.embedder import load_embedder
from app.second_brain.index import brain_index
from app.second_brain.store import load_all_embeddings_from_store

from app.api import (chat, chat_stream, graph, map_api, alerts, profile, brain, export_api,
                     audit, voice, health, dashboard, analytics, social, pattern_predict, osint_api, upload_api, live_stream,
                     evidence, products, briefing, sentinel, corridors, linkage, vigil, hypothesis, ops,
                     session_api, feedback, translate, jobs, dataset, docs_questions, obs, sdar,
                     forecast_api)


import asyncio

async def background_warmup():
    """Runs heavy initialization after the server has successfully bound to the port."""
    print("⏳ Starting background warmup tasks...")

    # Expand main.db.gz into /tmp before anything queries it. This used to run at module
    # import time, so ~276 MB of gzip inflation delayed the port bind on every Catalyst
    # cold start. It runs here now; any request that arrives first hits the same guard
    # (see app/core/db_path.ensure_db_staged) and waits rather than erroring.
    try:
        from app.core.db_path import ensure_db_staged
        await asyncio.to_thread(ensure_db_staged)
    except Exception as e:
        print(f"  database staging failed: {e}")

    # Load BGE-small-en-v1.5. Off the event loop: importing torch + transformers and
    # loading the weights is several seconds of blocking CPU work, and running it inline
    # would stall every request the server accepted in that window — the port is open by
    # now, so those requests are real.
    # Print the model that will ACTUALLY load. This was hardcoded to bge-small while
    # .env overrode BRAIN_EMBEDDING_MODEL to all-MiniLM-L6-v2, so the startup log
    # confidently named a model the process never touched.
    print(f"Loading Second Brain embedder ({settings.BRAIN_EMBEDDING_MODEL})...")
    try:
        await asyncio.to_thread(load_embedder)
    except Exception as e:
        print(f"  embedder failed: {e}")

    # Rebuild hot in-memory cosine index
    print("Rebuilding Second Brain index from Data Store...")
    try:
        rows = await load_all_embeddings_from_store()
        await asyncio.to_thread(brain_index.rebuild, rows)
        print(f"Second Brain index ready — {len(rows)} embeddings loaded")
    except Exception as e:
        print(f"  index rebuild failed: {e}")

    # Local demo seed
    if brain_index.size == 0:
        try:
            from app.second_brain.ingestion import seed_demo_brain
            _seeded = await asyncio.to_thread(seed_demo_brain)
            print(f"  Seeded {_seeded} planted brain summaries (local demo)")
        except Exception as e:
            print(f"  brain seed skipped: {e}")

    # Index MO_Details
    try:
        from app.second_brain.ingestion import index_mo_fields
        mo_count = await asyncio.to_thread(index_mo_fields)
        print(f"  MO field index: {mo_count} crime narrative(s) added to Brain")
    except Exception as e:
        print(f"  MO field indexing skipped: {e}")

    # Precompute full-graph metrics
    try:
        from app.services.graph_cache import refresh as refresh_graph
        gc = await asyncio.to_thread(refresh_graph)
        s = gc["stats"]
        print(f"  Graph cache ready — {s['node_count']} nodes")
    except Exception as e:
        print(f"  graph cache skipped: {e}")

    # Precompute per-district aggregates
    try:
        from app.services.district_cache import refresh as refresh_districts
        dc = await asyncio.to_thread(refresh_districts)
        print(f"  District cache ready — {len(dc)} zones")
    except Exception as e:
        print(f"  district cache skipped: {e}")

    # Warm Evidence Ledger
    try:
        from app.services.evidence_ledger import refresh as refresh_evidence
        ev = await asyncio.to_thread(refresh_evidence)
        print(f"  Evidence ledger ready — {ev['rows']} rows")
        from app.services.product_store import setup_default_products
        await asyncio.to_thread(setup_default_products)
        from app.core.memory import init_memory_db
        await asyncio.to_thread(init_memory_db)
    except Exception as e:
        print(f"  evidence ledger skipped: {e}")

    # Load cross-encoder — off the event loop for the same reason as the embedder.
    try:
        from app.second_brain.reranker import reranker as _brain_reranker
        ok = await asyncio.to_thread(_brain_reranker.load)
        print(f"  Brain reranker {'ready' if ok else 'unavailable (rerank degraded)'}")
    except Exception as e:
        print(f"  Brain reranker load skipped: {e}")

    # Pre-warm the unfiltered dataset overview — six unindexed aggregate scans over
    # 425k rows (~10s cold). Doing it here means the Brain screen's first load is
    # served from the product store instead of paying for it.
    try:
        from app.api.dataset import dataset_overview
        _ov = await asyncio.to_thread(lambda: asyncio.run(dataset_overview()))
        print(f"  Dataset overview cached — {_ov['total']:,} FIRs")
    except Exception as e:
        print(f"  dataset overview warm skipped: {e}")

    # The Full Data Set tab calls /summary, not /overview — ~6 s of aggregates at 1M FIRs,
    # during which every KPI tile read "0". Warm the unfiltered variant it opens with.
    try:
        from app.api.dataset import dataset_summary
        _sm = await asyncio.to_thread(lambda: asyncio.run(dataset_summary()))
        print(f"  Dataset summary cached — {_sm['total']:,} FIRs")
    except Exception as e:
        print(f"  dataset summary warm skipped: {e}")

    # The officer panels on the same tab (deadline clock, outcomes, 24-month trend): one
    # pass over the register, ~17 s cold at 1M FIRs. Filtered variants are sub-2 s.
    try:
        from app.api.dataset import dataset_officer_view
        _ofv = await asyncio.to_thread(lambda: asyncio.run(dataset_officer_view()))
        print(f"  Officer view cached — {_ofv['deadline']['open_total']:,} open investigations")
    except Exception as e:
        print(f"  officer view warm skipped: {e}")

    # Identity-link hypotheses shown beside every suspect search (~1.5 s of pairwise scoring,
    # kept with the world once computed): done here so the first search does not pay it.
    try:
        from app.services.entity_resolver import suggest_identity_links
        from app.services.zcql_local import _world
        _hyp = await asyncio.to_thread(suggest_identity_links, _world(), 0.75)
        print(f"  Identity links cached — {len(_hyp)} hypotheses")
    except Exception as e:
        print(f"  identity links warm skipped: {e}")

    # Pre-warm the full-dataset Crime Graph cycles (unfiltered). This populates the
    # product_store cache so the Brain screen's Crime Graph loads instantly.
    try:
        from app.api.dataset import dataset_cycles
        _cy = await asyncio.to_thread(lambda: asyncio.run(dataset_cycles()))
        print(f"  Dataset cycles cached — {_cy['total']:,} FIRs, {len(_cy['groups'])} groups")
        # Every year chip too: a cold year is 1-3s, which on stage reads as a filter that
        # did nothing. ~15s total, in the background, after the port is already bound.
        for _y in [y["year"] for y in _cy.get("years", [])]:
            await asyncio.to_thread(lambda y=_y: asyncio.run(dataset_cycles(y)))
        print(f"  Crime-graph years cached — {len(_cy.get('years', []))} chips")
    except Exception as e:
        print(f"  dataset cycles warm skipped: {e}")

    # Gi* surface warmup
    try:
        from app.services.anomaly import gi_star_surface as _gss
        _gi_zones = await asyncio.to_thread(_gss)
        print(f"  Gi* surface ready — {len(_gi_zones)} zones")
    except Exception as e:
        print(f"  Gi* surface warmup skipped: {e}")

    # Map forecasting store (geo_ok columns, geo_units, forecast_cube). Current → one
    # signature query; after an ingest or on a fresh deploy it rebuilds (~35 s at 1M FIRs).
    try:
        from app.forecast import store as _fstore
        _fs = await asyncio.to_thread(lambda: _fstore.ensure(check_now=True))
        print(f"  Forecast cube {'rebuilt in ' + str(_fs['seconds']) + 's' if _fs else 'current'}")
        # Forecasts for the configured as-of (ANTAR_FORECAST_AS_OF, default wall clock)
        # and for the end of the real record, which the back-test and model card read.
        # Current → read from forecast_meta; stale → ~70 s each, in the background.
        from app.forecast import run as _frun
        for _spec in (None, "real"):
            _fr = await asyncio.to_thread(lambda s=_spec: _frun.ensure(override=s))
            print(f"  Forecasts as of {_fr['as_of']} ({_fr['models']} models, "
                  f"{_fr['real_share']:.0%} real history)")
        # Gi* for the configured as-of, so /api/forecast/hotspots never waits 2 s for it
        from app.forecast import asof as _fasof, service as _fsvc
        await asyncio.to_thread(_fsvc.warm, _fasof.current().as_of)
    except Exception as e:
        print(f"  forecast store skipped: {e}")

    # Forecast scan
    try:
        from app.agents.forecast_agent import scan as _forecast_scan
        _fc = await asyncio.to_thread(lambda: _forecast_scan(session_id='startup'))
        print(f"  Forecast scan: {_fc['created']} active alert(s)")
    except Exception as e:
        print(f"  startup forecast scan skipped: {e}")

    # Heaviest analytics templates, run once so the first officer question is not the one
    # that pays for a cold page cache. T22 rebuilds one row per FIR and T23 groups beats
    # inside the largest district; both cache their result afterwards.
    try:
        import time as _qt
        from app.agents.query_agent import run_template as _rt
        _q0 = _qt.time()
        for _tid, _p in (("T22", {"dimension": "district"}),
                         ("T23", {"zones": ["Bengaluru City"]}),
                         ("T11", {}), ("T13", {}), ("T17", {})):
            await asyncio.to_thread(_rt, _tid, dict(_p))
        print(f"  Query warm-up done in {_qt.time() - _q0:.1f}s")
    except Exception as e:
        print(f"  query warm-up skipped: {e}")

    from app.services import llm as _llm
    _llm_on = _llm.available()
    _d = _llm.describe()
    print(f"Language model: {_d['provider']}" + (f" · {_d.get('model')} · {_d['where']}" if _llm_on else " · answers come from the records only"))

    if _llm_on and (_llm.provider() == "openai_compatible" or settings.QUICKML_CHAT_ENDPOINT_URL or settings.QUICKML_LLM_ENDPOINT_URL):
        # Deliberately generous: a cold QuickML endpoint takes ~75s on its first call
        # (OAuth mint + serving cold start), far past the 20s budget a live question gets.
        # Paying it here means the first officer question does not. Runs in the background
        # warmup task, so it never delays port binding.
        import time as _t
        _w0 = _t.time()
        from app.services.quickml import warm_up as _warm_up
        if await _warm_up():
            print(f"LLM warm-up OK (chat model) — {_t.time() - _w0:.1f}s")
        else:
            print(f"  LLM warm-up failed after {_t.time() - _w0:.1f}s — "
                  "answers will use the deterministic path")

    # Production orchestration
    try:
        from app.core import orchestrator
        orchestrator.register_default_fleet()
        orchestrator.start_autonomous(interval_s=60)
        print("Orchestrator online")
    except Exception as e:
        print(f"  Orchestrator failed: {e}")

    if settings.OBS_ENABLED:
        try:
            from app.obs import store
            store.init_db()
            print("Observability DB ready")
        except Exception as e:
            print(f"  Observability init skipped: {e}")

    print("Background warmup completed successfully!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Yield immediately to bind port, run heavy loads in background."""
    print("Antar starting up...")
    _posture = security.posture()
    print(f"Security posture: {'production' if _posture['production'] else 'development'}, "
          f"identity={_posture['auth_mode']}")
    for _w in _posture["warnings"]:
        print(f"  SECURITY: {_w}")
    security.enforce_posture(_posture)
    # What runs must be what was reviewed: agent modules and system prompts against
    # agents.lock.json. A warning in development; in production a mismatch stops here.
    from app.agents import agent_lock
    _lock = agent_lock.enforce(_posture["production"])
    print(f"Agents and prompts: {'in step with the lock' if _lock['ok'] else 'DIFFER from agents.lock.json'}"
          f" (prompt version {_lock.get('prompt_version')})")
    for _c in (_lock.get("changed") or [])[:8]:
        print(f"  LOCK: {_c}")
    
    # Stage the database BEFORE anything is served. It takes about 3 seconds; done in the
    # background instead, the first request (a health probe, written to the audit log)
    # opened the path first, sqlite created an empty file there, and staging then took
    # that file for the registry. The whole deployment ran on an empty database.
    try:
        from app.core.db_path import ensure_db_staged
        await asyncio.to_thread(ensure_db_staged)
    except Exception as e:
        print(f"  database staging failed: {e}")

    # Start real-time dispatch simulator task in the background
    from app.api.live_stream import start_dispatch_simulator
    simulator_task = asyncio.create_task(start_dispatch_simulator())
    print("Real-time emergency dispatch simulator started")
    
    # Kick off the heavy warmup in the background so Uvicorn can yield and bind the port instantly
    warmup_task = asyncio.create_task(background_warmup())
    
    print("Port binding permitted — serving requests")
    yield
    print("Antar shutting down")
    from app.core import orchestrator
    orchestrator.stop_autonomous()
    simulator_task.cancel()
    warmup_task.cancel()
    from app.services.quickml import aclose_client
    await aclose_client()


# API docs publish every route, parameter and schema — a map for an attacker. Hidden in
# production unless ANTAR_EXPOSE_DOCS=true is set deliberately for a debugging window.
_docs_on = (not security.is_production()) or settings.ANTAR_EXPOSE_DOCS
app = FastAPI(
    title="Antar",
    description="Multi-Agent Crime Intelligence Platform — Datathon 2026",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_on else None,
    redoc_url="/redoc" if _docs_on else None,
    openapi_url="/openapi.json" if _docs_on else None,
)

# CORS — allow the Next.js frontend (Web Client origin set via ALLOWED_ORIGINS env).
# allow_credentials MUST stay False: the Catalyst AppSail gateway already injects its own
# `Access-Control-Allow-Credentials` header, so enabling it here produces a DUPLICATE
# credentials header that browsers reject. FastAPI still emits the Allow-Origin header
# (the gateway does not), so cross-origin calls work with exactly one of each header.
# The app never relies on cross-origin cookies (session_id travels in the request body).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Role", "X-Officer", "X-Cron-Secret",
                   "X-Session-Id", "Accept", "Accept-Language"],
    expose_headers=["x-trace-id", "x-call-chain-id"],
)


# Compress responses over 1 KB. Several screens load large JSON (the crime graph is
# 1.8 MB, the forecast list 94 KB, the heat layer 67 KB); over a deployed link that is
# the difference between a page that appears and one that crawls. The chat stream is left
# alone: it is sent token by token and must not wait in a compression buffer. Audio is
# already compressed.
from starlette.middleware.gzip import GZipMiddleware as _GZip


class _Compress(_GZip):
    _SKIP = ("/api/chat/stream", "/api/chat_stream", "/api/voice")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith(self._SKIP):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


app.add_middleware(_Compress, minimum_size=1024)

@app.middleware("http")
async def _obs_mw(request, call_next):
    from app.obs import trace
    started = trace.start(surface="http", question=request.url.path, env="appsail")
    try:
        resp = await call_next(request)
        if started:
            resp.headers["x-trace-id"] = started
        return resp
    finally:
        if trace.current():
            trace.close(answer=str(resp.status_code) if 'resp' in locals() else "error")

# Signed-token gateway (no-op in header mode). Registered BEFORE the audit middleware so
# the audit middleware wraps it: a refused call is still written to the audit log.
install_gateway(app)

# Audit every API call (M10) — dev: officer/role from headers; deploy: from Catalyst Auth.
@app.middleware("http")
async def _audit(request, call_next):
    # One security context per request, bound here at the outermost layer so everything
    # the request runs - agents, traces, the audit row below - shares one call chain.
    from app.core import security_context
    path = request.url.path
    ident = resolve_identity(request)
    officer, role = (ident.officer, ident.role) if ident else ("anonymous", "none")
    ctx, token = security_context.begin(officer, role, session_id=request.headers.get("x-session-id", "")[:128],
                                        posting=getattr(ident, "posting", "") if ident else "")
    try:
        response = await call_next(request)
    finally:
        security_context.end(token)
    response.headers["x-call-chain-id"] = ctx.call_chain_id
    # Not recorded: health probes, and CORS pre-flight checks. A browser sends an OPTIONS
    # request, without credentials by design, before each cross-origin call; recorded,
    # they filled the ledger with "anonymous" rows that read like unauthenticated access.
    if path.startswith("/api/") and not path.startswith("/api/health") and request.method != "OPTIONS":
        audit_store.record(officer, role, request.method, path, response.status_code, extra=ctx.for_audit())
    return response


# ── API Routers ──────────────────────────────────────────────────────────────
_inspector = [Depends(require_role("Inspector"))]
app.include_router(health.router,      prefix="/api",        tags=["Health"])
from app.api import auth_api
app.include_router(auth_api.router,    prefix="/api/auth",   tags=["Sign-in"])
app.include_router(chat.router,        prefix="/api/chat",        tags=["Chat"])
app.include_router(chat_stream.router, prefix="/api/chat",        tags=["Chat Stream"])
app.include_router(dashboard.router,   prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(analytics.router,    prefix="/api/analytics", tags=["Analytics"])
app.include_router(dataset.router,     prefix="/api/dataset",  tags=["Dataset"])
app.include_router(docs_questions.router, prefix="/api/docs", tags=["Docs API"])
app.include_router(social.router,        prefix="/api/social",  tags=["Social"])
app.include_router(voice.router,       prefix="/api/voice",  tags=["Voice"])
app.include_router(graph.router,       prefix="/api/graph",  tags=["Graph"],   dependencies=_inspector)
app.include_router(map_api.router,     prefix="/api/map",    tags=["Map"])
app.include_router(forecast_api.router, prefix="/api/forecast", tags=["Map Forecast"])
app.include_router(alerts.router,      prefix="/api/alerts", tags=["Alerts"],  dependencies=_inspector)
app.include_router(profile.router,     prefix="/api/profile",tags=["Profile"], dependencies=_inspector)
app.include_router(brain.router,       prefix="/api/brain",  tags=["Brain"],   dependencies=_inspector)
app.include_router(export_api.router,  prefix="/api/export", tags=["Export"])
app.include_router(export_api.report_router,                 tags=["Report"])
app.include_router(audit.router,       prefix="/api/audit",  tags=["Audit"],   dependencies=[Depends(require_role("Admin"))])
app.include_router(audit.derivation_router, prefix="/api/derivation", tags=["Derivation"], dependencies=_inspector)
app.include_router(pattern_predict.router, prefix="/api",    tags=["Pattern Predict"])
app.include_router(osint_api.router,   prefix="/api/osint",  tags=["OSINT"])
app.include_router(upload_api.router,  prefix="/api/upload", tags=["Upload"])
app.include_router(live_stream.router, prefix="/api/stream", tags=["Live Stream"])
app.include_router(evidence.router,    prefix="/api/evidence", tags=["Evidence Ledger"])
app.include_router(products.router,    prefix="/api/products", tags=["Products Store"])
app.include_router(briefing.router,    prefix="/api/briefing", tags=["Shift Briefing"])
app.include_router(sentinel.router,    prefix="/api/sentinel", tags=["Sentinel Watchdog"])
app.include_router(corridors.router,   prefix="/api/corridors", tags=["Corridor Intelligence"])
app.include_router(linkage.router,     prefix="/api/linkage", tags=["MO Case-Matcher"])
from app.api import case_api
app.include_router(case_api.router,   prefix="/api/case", tags=["Case Timeline"], dependencies=[Depends(require_role("Constable"))])
from app.api import money_api
app.include_router(money_api.router,  prefix="/api/money", tags=["Money Trail"], dependencies=_inspector)
app.include_router(vigil.router,       prefix="/api/vigil", tags=["Vigil Compliance Auditor"])
app.include_router(hypothesis.router,  prefix="/api", tags=["Hypothesis Lifecycle"])
app.include_router(ops.router,         prefix="/api/orchestrator", tags=["Orchestrator Ops"])
app.include_router(session_api.router, prefix="/api/session", tags=["Encrypted Sessions"])
app.include_router(feedback.router,    prefix="/api/feedback", tags=["Answer Feedback"])
app.include_router(translate.router,   prefix="/api/translate", tags=["Translate"])
app.include_router(jobs.router,        prefix="/api/jobs", tags=["Long-Task Jobs"])
from app.api import forensic, workspace, adversarial_audit_api, hitl_api
app.include_router(forensic.router)
app.include_router(hitl_api.router, prefix="/api/hitl", tags=["Human-in-the-Loop"])
app.include_router(adversarial_audit_api.router, prefix="/api/adversarial-audit",
                   tags=["Adversarial Audit"], dependencies=_inspector)
app.include_router(workspace.router,   prefix="/api/workspace", tags=["Workspace"])
# Runs suspect-level agents, so it is gated like /api/graph and /api/profile.
from app.api import console
app.include_router(console.router,     prefix="/api/console", tags=["Brain Console"], dependencies=_inspector)
app.include_router(obs.router,         tags=["Observability"])
app.include_router(sdar.router,        prefix="/api/obs", tags=["SDAR"])

# Outermost layer: generic error bodies (no exception text, paths or secrets ever reach a
# caller), security headers on every response, and the request-body ceiling.
security.install(app)
