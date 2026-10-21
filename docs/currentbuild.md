# Antar - Current Build Documentation

Reverse-engineered from the working tree at `D:\Project`.
Code is the source of truth. Every claim cites `path:line`.

| Item | Value |
|---|---|
| Documented on | 2026-10-13 |
| Git HEAD | `a534b37` (78 commits, no remote configured) |
| Working tree | HEAD plus 25 untracked root scratch files |
| Reference snapshot | `D:\Antar_FinalBuild_Dev` (read-only, context only) |
| Source edits made | None. This file is the only file written. |
| Side effect | Opening 5 SQLite files read-only made SQLite create 10 sidecar files (`*.db-shm`, `*.db-wal`) next to `main.db` and the four `obs` databases. They are git-ignored runtime files, hold no data, and SQLite reuses them. Later passes open databases in immutable mode to avoid this. |

## Tag legend

| Tag | Meaning |
|---|---|
| [VERIFIED] | I read the code or ran a read-only command that shows this |
| [INFERRED] | Reasoned from code; the basis is stated |
| [STUB/MOCK] | Exists but is hardcoded, simulated, unreachable or demo-only |
| [NOT FOUND] | Looked for it; it is not in the code |

## Pass status

| Pass | Title | Status |
|---|---|---|
| 0 | Inventory | Done |
| 1 | Main entity and architecture | Pending |
| 2 | Login, session and access | Pending |
| 3 | Navigation map | Pending |
| 4 | Page by page | Pending |
| 5 | Backend API catalog | Pending |
| 6 | Backend function catalog | Pending |
| 7 | Data layer | Pending |
| 8 | AI, engines and special logic | Pending |
| 9 | Integrations and infrastructure | Pending |
| 10 | Security, validation and error handling | Pending |
| 11 | What makes it good | Pending |
| 12 | End-to-end user journeys | Pending |
| 13 | Coverage audit | Pending |

## Working assumptions

Eight questions were asked before Pass 0 and are still open.
Until answered, the document uses these defaults.

| # | Open question | Default used |
|---|---|---|
| 1 | Which USP list is canonical | The 10 in `app/core/antar_identity.py:65-76` (code wins, R1); the 3 in `info.md:71-79` are cross-referenced |
| 2 | Voice: Dwani only, or Bhashini and gTTS too | Document all three as found and flag the conflict |
| 3 | Which frontend folder | `D:\Project\antar-frontend` |
| 4 | Duplicate-looking pages | All 24 page files documented; unlinked ones marked |
| 5 | Role of the reference folder | Context only; not documented |
| 6 | Is a deployment live | Hosting described as configured, not verified live |
| 7 | May synthetic data be named plainly | Yes; this file is treated as internal |
| 8 | Scope of inventory | Everything listed; deep passes cover `app/`, `main.py`, `antar-frontend/` |

---

# PASS 0 - INVENTORY

Plain English: this pass is the parts list. It says what folders
exist, what software the build is made of, how it starts, how to
run and test it, which settings it reads, and how many of each
thing there are. Later passes explain how the parts behave.

Method: read-only listing and static parsing. Python files were
parsed with the `ast` module (no code was imported or executed).
SQLite files were opened read-only to list table names only.
The test suite was NOT run (see flag F0-22).

## 0.1 Directory tree (3 levels)

File counts exclude `.git`, `.venv`, `node_modules`,
`__pycache__`, `.next` and `.pytest_cache`.

```
D:\Project
|- main.py              FastAPI entry point; mounts every router
|- run.py               Container launcher; picks the port, runs uvicorn
|- app/                 Backend package (185 .py, 39,733 lines)
|  |- agents/     39    Agents, router, answer writers, LangGraph graph
|  |- api/        45    FastAPI routers (HTTP endpoints)
|  |- config/      2    prompt_loader.py + intent_taxonomy.json
|  |- core/       26    Settings, auth, security, HITL, orchestrator
|  |- forecast/   12    Map forecasting: features, model, back-test
|  |- graph/       1    intent_flow.py (no importer found, see F0-7)
|  |- obs/        12    Observability: traces, flags, judge, eval set
|  |- second_brain/ 11  Embedder, vector index, reranker, retrieval
|  |- seeds/      34    Synthetic data generator and loaders
|  |  |- data/     1    fir_synthetic.csv (1.29 MB)
|  |  |- out/     13    Generated seed JSON (crimes, suspects, ...)
|  |  |- out.bak/ 13    Older copy of the same 13 seed files
|  |- services/   28    Data access, LLM client, caches, anomaly, OSINT
|  |- tools/       3    Intent classifiers + tool registry
|- antar-frontend/      Next.js web client (195 files + out/)
|  |- app/        30    Routes (App Router) + globals.css
|  |  |- (app)/   24    Signed-in screens, wrapped by AppShell
|  |  |- (auth)/   3    Login screens, no chrome
|  |- components/ 53    51 .jsx components + 2 .rej patch leftovers
|  |  |- docs/     4    Animation pieces for the /docs page
|  |  |- ui/       1    neurons-hero.jsx
|  |- lib/        13    API client, auth, chat stream, map helpers
|  |- public/     72    Static assets
|  |  |- brand/    4    Logo files
|  |  |- fonts/   16    Local .woff2 fonts
|  |  |- mascots/ 48    Agent mascot .webp images
|  |- client/      4    Catalyst web-client scaffold ("testApp")
|  |- out/        78    Static HTML export dated 2026-09-15 (stale)
|  |  |- (22 folders)   One per exported page; named below
|  |- _unshipped/ 13    Brand art and data kept out of the build
|  |  |- brand/   11    Logos and a background video
|  |  |- data/     2    Older CSV and GeoJSON
|- tests/        109    106 test files + conftest, golden_queries, __init__
|- scripts/       25    One-off tools: export, benchmark, tokens
|- docs/          27    Product docs, pitches, security, back-test
|  |- footprint/  13    Measured disk and memory reports
|- knowledge/    207    Generated knowledge bundle (OKF v0.2)
|  |- agents/     21    One page per declared agent
|  |- statutes/   40    Top acts by volume
|  |- taxonomy/  114    Crime groups
|  |- templates/  23    Query template pages
|  |- vocabulary/  3    How words resolve to the record
|- models/        16    ONNX model exports + README
|  |- onnx/       14    Exported models (see 0.2.4)
|  |  |- BAAI--bge-small-en-v1.5/                  5  Embedder
|  |  |- all-MiniLM-L6-v2/                         5  Alt embedder
|  |  |- cross-encoder--ms-marco-MiniLM-L-6-v2/    4  Reranker
|- data/           6    Second copy of the databases (see F0-11)
|  |- obs/         2    obs.db and case_file.db (not the live path)
|- data_sessions/  7    Encrypted session files + live obs data
|  |- obs/         3    obs.db, case_file.db, obs_spans.jsonl
|- graphify-out/ 440    Knowledge-graph tool output (not runtime)
|  |- cache/     266    Parsed-AST cache
|  |  |- ast/    265    One cache entry per parsed file
|  |- wiki/      164    Generated wiki pages
|- gstack/      2597    Third-party tooling (see note below)
|- .agents/rules/  2    Rule files for coding assistants
|- .claude/        1    launch.json (dev-server launch config)
```

Purpose evidence:

| Folder | Evidence for the stated purpose |
|---|---|
| `app/agents` | Module docstrings, e.g. `app/agents/graph.py:1-3`, `app/agents/query_agent.py:1-3` |
| `app/api` | Routers mounted at `main.py:401-449` |
| `app/core` | `app/core/settings.py:1-4`, `app/core/hitl.py:1-3`, `app/core/orchestrator.py:1-3` |
| `app/forecast` | `app/forecast/__init__.py:1-2` |
| `app/second_brain` | `app/second_brain/embedder.py:1-3`, `vec_store.py:1-3` |
| `app/seeds` | `app/seeds/generator.py:1-3` ("Synthetic World Generator") |
| `app/services` | `app/services/zcql_repo.py:1-3`, `quickml.py:1-3` |
| `antar-frontend/app` | `antar-frontend/app/(app)/layout.jsx:1-5`, `app/(auth)/layout.jsx:1-3` |
| `antar-frontend/client` | `client/index.html` title "testApp", body "Hello World" [STUB/MOCK] |
| `knowledge` | `knowledge/index.md:1-3` (`okf_version: "0.2"`); written by `scripts/build_okf_bundle.py:1-2` |
| `models` | `models/README.md:1`; ONNX files written by `scripts/export_onnx_models.py` |
| `data_sessions` | `.env` sets `OBS_DIR` to `data_sessions\obs`; `.enc` files come from `app/api/session_api.py:1-3` |

Note on `gstack/`: it is a separate git repository
(`github.com/garrytan/gstack`, version 1.89.1 per
`gstack/package.json`), tracked in this repo as one gitlink entry.
It has 74 subfolders and 2,597 files. It is developer tooling, not
Antar code. It is excluded from both deploy paths
(`.dockerignore:98`, `.appignore:38-39`). Its subfolders are not
documented further. [VERIFIED]

Note on `graphify-out/`: 440 tracked files of generated graph
output. Excluded from deploys (`.dockerignore:99`,
`.appignore:32-33`). Not read by any backend module. [INFERRED:
no reference to `graphify` in `app/` import scan]

The 22 folders inside `antar-frontend/out/`: `404`, `_next`,
`about`, `account`, `admin`, `antar`, `antarBrain`, `ask`,
`brain`, `brand`, `docs`, `guide`, `info`, `login`, `map`,
`network`, `predict`, `profiles`, `search`, `social`, `trace`,
`trends`. There is no `approvals` folder (see F0-1).

Folders found: 81 (13 at level 1, 30 at level 2, 38 at level 3;
excluding the 74 inside gstack and the six tool folders `.git`,
`.venv`, `node_modules`, `__pycache__`, `.next`,
`.pytest_cache`). Folders documented: 81.

### 0.1.1 Root files (71)

| Group | Count | Files |
|---|---|---|
| Entry and config | 12 | `main.py`, `run.py`, `requirements.txt`, `requirements-runtime.txt`, `pytest.ini`, `Dockerfile`, `Dockerfile.onnx`, `catalyst.json`, `app-config.json`, `.dockerignore`, `.appignore`, `.gitignore` |
| Docs | 6 | `AGENTS.md`, `info.md`, `PROGRESS.md`, `RUN.md`, `final_backend.md`, `prompt_lib.json` |
| Databases and vectors | 12 | `main.db`, `main.db.gz`, `main.db.pre1m.bak-shm`, `main.db.pre1m.bak-wal`, `intelligent.db`, `brain_vectors.db`, `brain_vectors.i8`, `brain_vectors.ids`, `brain_vectors.mult`, `.bench_snap_test.db` (0 bytes), `.snap_vacuum.db` (0 bytes), `data_feedback.jsonl` |
| Secrets and identity (values not read) | 7 | `.env`, `.env.bak-20260923`, `.env.example`, `.session_key`, `.catalystrc.bak`, `auth_users.json`, `auth_local_credentials.txt` |
| Scratch patch scripts | 26 | `run_update.ps1`, `run_update2.ps1`, `run_update3.py` to `run_update14.py` (12), `run_update_15.py`, `run_update_16.py`, `run_update_chat_guide.py`, `run_update_css.py`, `run_update_css_columns.py`, `update_guide.py`, `fix_agents.py`, `fix_assemble.py`, `fix_as_of.py`, `fix_mascot_7.py`, `fix_terminal_style.py`, `find_emojis.js` |
| Ad-hoc tests and output | 8 | `benchmark_query.py`, `profile_pipeline.py`, `run_40_questions_test.py`, `test_40_questions_report.json`, `test_rlhf.py`, `test_routes.py`, `test_stream_timing.py`, `out.txt` |

Root files found: 71. Root files listed: 71.

The 26 scratch patch scripts are one-off text-replacement
scripts. All 26 are excluded from the Docker image
(`.dockerignore:93-96`). The AppSail ignore file excludes only
the `run_update*` ones (`.appignore:40`); `fix_*.py`,
`update_guide.py` and `find_emojis.js` are not listed there.
[VERIFIED]

## 0.2 Detected stack

Plain English: the backend is a Python web server, the frontend
is a React website, the data lives in SQLite files, and the AI
parts are a hosted language model plus small local models.

### 0.2.1 Languages and runtimes

| Layer | Language / runtime | Version | Evidence |
|---|---|---|---|
| Backend | Python | 3.11.15 (local venv) | `.venv` reports 3.11.15; `RUN.md:8` |
| Backend (container) | Python | 3.11 | `Dockerfile:1`, `app-config.json:3` |
| Frontend | JavaScript (JSX), 1 TypeScript file | Node 24.16.0, npm 11.13.0 (local) | `node --version`; `lib/brand.ts` |
| Database | SQL (SQLite dialect) | SQLite via Python stdlib | `app/services/zcql_local.py:1-3` |
| Styles | CSS | one 416 KB stylesheet | `antar-frontend/app/globals.css` |

`main.py:3` says "Python 3.12". Every other source says 3.11,
and `RUN.md:30-31` says do not use 3.12. See F0-8.

### 0.2.2 Backend libraries (runtime set)

Source: `requirements-runtime.txt:17-55` (24 pinned packages).
All 24 are installed in `.venv` at the pinned version. [VERIFIED
with `pip list`]

| Library | Version | What it is | Used here |
|---|---|---|---|
| fastapi | 0.115.5 | Python web framework for HTTP APIs | `main.py:73`, `main.py:344`; 52 files |
| uvicorn | 0.32.1 | Server that runs a FastAPI app | `run.py:15`, `run.py:34` |
| python-multipart | 0.0.17 | Parser for file-upload forms | `app/api/upload_api.py:7`, `app/api/voice.py:8` |
| httpx | 0.27.2 | Async HTTP client | `app/services/quickml.py:10`, `bhashini.py:10`, `osint.py:8`, `events.py:157` |
| pydantic | 2.9.2 | Data validation by typed models | 24 files, e.g. `app/agents/intent_parser.py:23` |
| pydantic-settings | 2.6.1 | Loads settings from env and `.env` | `app/core/settings.py:9` |
| langgraph | 0.6.11 | Library for agent workflows as a graph | `app/agents/state.py:9`, `checkpoint_store.py:42` |
| langchain-core | 0.3.86 | Base types LangGraph depends on | No direct import found; transitive [INFERRED] |
| langgraph-checkpoint | 3.0.1 | Saves graph state between turns | `app/agents/checkpoint_store.py:42` |
| langgraph-prebuilt | 0.6.5 | Ready-made LangGraph parts | No direct import found; required by langgraph (`requirements.txt:24`) |
| typing-extensions | 4.10.0 | Backported typing features | Hard pin for the Catalyst SDK (`requirements.txt:27`) |
| zcatalyst-sdk | 1.0.1 | Zoho Catalyst cloud SDK | `app/core/catalyst.py:28` |
| onnxruntime | 1.30.0 | Runs exported neural models without PyTorch | `app/second_brain/onnx_backend.py:46`, `main.py:68` |
| tokenizers | 0.22.2 | Splits text into model tokens | `app/second_brain/onnx_backend.py:68` |
| scikit-learn | 1.4.1.post1 | Classical machine-learning library | `app/forecast/model.py:219`, `app/services/patterns.py:20` |
| pandas | 2.2.1 | Table data library | `app/forecast/store.py:147` |
| scipy | 1.12.0 | Scientific computing library | `app/forecast/features.py:43`, `store.py:118` |
| numpy | 1.26.4 | Array maths library | 18 files, e.g. `app/forecast/model.py:46` |
| networkx | 3.6.1 | Graph analysis (PageRank, communities) | `app/agents/network_agent.py:27`, `app/services/graph_cache.py:30` |
| python-dotenv | 1.0.1 | Loads `.env` files | `run.py:22` |
| structlog | 24.4.0 | Structured logging | 13 files, e.g. `app/agents/manifest.py:30` |
| beautifulsoup4 | 4.15.0 | HTML parser | `app/services/osint.py:9` |
| cryptography | 42.0.5 | Encryption library (Fernet) | `app/api/session_api.py:28` |
| gTTS | 2.5.1 | Google text-to-speech client | `app/api/voice.py:14` |

Also present:

| Library | Version | Where | Note |
|---|---|---|---|
| starlette | 0.41.3 | transitive via fastapi | `app/core/security.py:173` |
| sqlite3 | stdlib | 42 files | e.g. `app/agents/checkpoint_store.py:34` |
| sentence-transformers | 3.0.1 | `requirements.txt:57` only | Dev/export path; NOT in `.venv`. Imported lazily at `app/second_brain/embedder.py:51`, `reranker.py:74` |
| torch | 2.5.1 (CPU) | `Dockerfile:28-30` only | No direct import in `app/`; NOT in `.venv` |
| onnx | 1.23.0 | `Dockerfile.onnx:46` only | Export stage only |
| llama_cpp | not pinned anywhere | `app/tools/local_intent_classifier.py:7` | Not installed; model file absent (`Dockerfile:60-63`) [STUB/MOCK] |
| pytest | 8.3.4 | test only | `RUN.md:21` |
| psutil | 7.2.2 | test only | `RUN.md:21`, `RUN.md:24-28` |

Backend runtime libraries found: 24. Documented: 24.

### 0.2.3 Frontend libraries

Source: `antar-frontend/package.json:11-33` (21 dependencies,
0 devDependencies). Installed versions read from `node_modules`.

| Library | Installed | What it is | Used here |
|---|---|---|---|
| next | 14.2.35 | React framework with file-based routes | `app/page.jsx:4`; 34 files |
| react | 18.3.1 | UI component library | 68 files |
| react-dom | 18.3.1 | Renders React to the browser | `components/ForecastPanel.jsx:13`; 4 files |
| framer-motion | 12.42.2 | Animation library | `app/(app)/about/page.jsx:4`; 10 files |
| lucide-react | 1.23.0 | Icon set | `app/(app)/about/page.jsx:5`; 21 files |
| leaflet | 1.9.4 | Interactive map library | `components/ForecastPanel.jsx:15`; 3 files |
| react-leaflet | 4.2.1 | React wrapper for Leaflet | `components/ForecastPanel.jsx:14`; 4 files |
| vis-network | 10.1.0 | Network-graph drawing | `components/NetworkGraph.jsx:16` |
| force-graph | 1.51.4 | 2D force-directed graph | `components/Constellation.jsx:127` |
| 3d-force-graph | 1.80.0 | 3D force-directed graph | `components/CaseBrain.jsx:74`; 2 files |
| globe.gl | 2.46.1 | 3D globe view | `components/GlobeMap.jsx:34` |
| recharts | 3.9.1 | Chart components | `components/DataOverview.jsx:9` |
| @xyflow/react | 12.11.1 | Node-and-edge flow diagrams | `app/(app)/predict/PredictScreen.jsx:14` |
| topojson-client | 3.1.0 | Reads TopoJSON map shapes | `components/MapScreen.jsx:10` |
| page-mascot | 0.1.0 | Animated mascot component | `app/(app)/docs/page.jsx:10`; 4 files |
| maplibre-gl | 6.11.2 | Vector map renderer | No import found [INFERRED unused] |
| hls.js | 1.6.16 | Video stream player | No import found [INFERRED unused] |
| animate.css | 4.1.1 | CSS animation classes | No import found [INFERRED unused] |
| vis-data | 8.0.4 | Data sets for vis-network | No direct import; peer of vis-network |
| react-is | 19.2.7 | React type checks | No direct import; peer of recharts [INFERRED] |
| postcss | 8.5.23 | CSS processing tool | Used by the Next build, no config file |

Frontend libraries found: 21. Documented: 21.

Tailwind CSS (a utility-class CSS framework) has a config file
(`antar-frontend/tailwind.config.js:1-36`) and three directives
(`app/globals.css:1-3`), but the `tailwindcss` package is NOT
installed and there is no `postcss.config.*`. See F0-4.

There is no `next.config.*` file. See F0-1.
TypeScript and ESLint are not installed. `npm run lint` has
nothing to run with. [VERIFIED: absent from `node_modules`]

### 0.2.4 Models and engines on disk

| Asset | Size | What it is | Evidence |
|---|---|---|---|
| `models/onnx/BAAI--bge-small-en-v1.5/` | 133 MB fp32 + 34 MB int8 | Text-embedding model (384 numbers per text) | `Dockerfile.onnx:99-102` |
| `models/onnx/all-MiniLM-L6-v2/` | 90 MB fp32 + 23 MB int8 | Alternative embedding model | `Dockerfile:46-52` |
| `models/onnx/cross-encoder--ms-marco-MiniLM-L-6-v2/` | 91 MB | Reranker: scores a query against a passage | `Dockerfile.onnx:100` |
| `brain_vectors.db` | 85.6 MB | Vector store, 1 table `brain_vectors` | read-only schema query |
| `brain_vectors.i8` / `.ids` / `.mult` | 38.4 MB / 1.2 MB / 0.4 MB | Memory-mapped int8 vector index and its id and scale files | `AGENTS.md` brain notes; detail in Pass 8 |
| `models/intelligent.db` | 0 bytes | Empty file | [STUB/MOCK] |
| `models/phi2.ggml` | absent | Local LLM the README asks for | `models/README.md:1` [NOT FOUND] |

Hosted LLMs (large language models reached over HTTP on Zoho
Catalyst QuickML) are named in settings, not stored on disk:
`app/core/settings.py:42-49`. Detail in Pass 8 and Pass 9.

### 0.2.5 Build and deploy tooling

| Tool | Present | Evidence |
|---|---|---|
| Docker | Two Dockerfiles; Docker Desktop installed locally | `Dockerfile:1-71`, `Dockerfile.onnx:1-108` |
| Zoho Catalyst AppSail config | Yes | `catalyst.json:1-9`, `app-config.json:1-15` |
| Zoho Catalyst web client config | Yes | `antar-frontend/catalyst.json` (`"source": "out"`) |
| CI pipeline | [NOT FOUND] | No `.github/` or `*.yml` in the project root |
| Git remote | [NOT FOUND] | `git remote -v` prints nothing |
| Python venv | Yes, torch-free | `RUN.md:8-14` |

## 0.3 Entry points

Plain English: these are the files where things start.

| Entry point | What starts there | Evidence |
|---|---|---|
| `main.py` | The FastAPI `app` object | `main.py:344-352` |
| `main.py` lifespan | Boot: simulator task + background warm-up | `main.py:312-338` |
| `run.py` | Container start: resolve port, `uvicorn.run` | `run.py:13-34` |
| `Dockerfile` CMD | `python3 run.py` | `Dockerfile:71`, `Dockerfile.onnx:108` |
| `app-config.json` command | `python3 -m uvicorn main:app` on the Catalyst port | `app-config.json:4` |
| `antar-frontend/app/layout.jsx` | Root HTML shell, fonts, theme and language providers | `app/layout.jsx:10-45` |
| `antar-frontend/app/page.jsx` | Entry gate: clears the session, redirects to `/login` | `app/page.jsx:8-17` |
| `antar-frontend/app/(app)/layout.jsx` | Wraps signed-in screens in `AppShell` | `(app)/layout.jsx:1-5` |
| `python -m app.agents.manifest` | Prints the live agent table | `AGENTS.md` "Known gaps" section |
| `python -m app.forecast.run` / `.backtest` | Offline forecast fit and back-test | `main.py:40-41` |
| `.claude/launch.json` | Two dev-server launch entries (ports 8000, 3000) | `.claude/launch.json` |

Two container start commands exist and differ: the Dockerfile
runs `run.py`; `app-config.json` runs uvicorn directly. The
Dockerfile says the Docker path does not read `app-config.json`
(`Dockerfile:8-11`). [VERIFIED]

Entry points found: 11. Documented: 11.

## 0.4 Commands: run, build, test, deploy

| Purpose | Command | Source |
|---|---|---|
| Build the venv | `python -m venv D:\Project\.venv` then `pip install -r requirements-runtime.txt pytest==8.3.4 psutil` | `RUN.md:19-21` |
| Run backend (local) | `D:\Project\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000` | `RUN.md:44` |
| Run backend (container style) | `python run.py` | `run.py:13-34` |
| Health check | `curl -s http://127.0.0.1:8000/api/health` | `RUN.md:68` |
| Run frontend (dev) | `npm run dev` in `antar-frontend` | `package.json:6` |
| Build frontend | `npm run build` (`next build`) | `package.json:7` |
| Serve built frontend | `npm run start` (`next start`) | `package.json:8` |
| Lint frontend | `npm run lint` (ESLint not installed) | `package.json:9` |
| Run all tests | `.\.venv\Scripts\python.exe -m pytest -q` (about 12 minutes) | `RUN.md:99-102` |
| Agent manifest test | `pytest tests/test_agents_manifest.py` | `AGENTS.md` "Adding an agent" step 3 |
| Create or change an account | `python scripts\set_password.py U-7001 Admin --name "..."` | `RUN.md:89` |
| Print accounts for a container | `python scripts\set_password.py --show-env` | `RUN.md:93` |
| Mint a signed token | `python scripts/mint_token.py <id> <role>` | `scripts/mint_token.py:1-2` |
| Export ONNX models | `python scripts/export_onnx_models.py --model ...` | `Dockerfile.onnx:59-61` |
| Build images | `docker build -f Dockerfile.onnx -t antar-api:onnx .` and `-f Dockerfile -t antar-api:torch .` | `Dockerfile.onnx:6-7` |
| Deploy backend | [NOT FOUND] as a script. `Dockerfile:8-11` says AppSail pulls a custom runtime image from Docker Hub. `catalyst deploy` appears only in prose at `docs/SECURITY.md:30` | - |
| Deploy frontend | [NOT FOUND] as a script. `antar-frontend/catalyst.json` points the web client at `out/` | - |

Test rule: stop the backend before running pytest. The suite
runs against the real `main.db` and removes rows added during
the run (`RUN.md:102-105`). [VERIFIED in docs; behaviour to be
confirmed from `tests/conftest.py` in Pass 7]

### 0.4.1 Scripts in `scripts/` (25)

Purpose is the script's own docstring unless marked.

| Script | Purpose |
|---|---|
| `ab_near_repeat.py` | A/B test: does the near-repeat forecast feature help |
| `bench_blas_threads.py` | Benchmark the BLAS thread cap (memory vs speed) |
| `benchmark_llm.py` | LLM benchmark [INFERRED from name; no docstring] |
| `benchmark_retrieval.py` | Retrieval benchmark [INFERRED from name] |
| `build_brain_index.py` | Build the Second Brain FIR vector corpus |
| `build_end_to_end_guide.js` | Builds the End-to-End Guide document [INFERRED from name] |
| `build_okf_bundle.py` | Export the knowledge layer to `./knowledge` (OKF v0.2) |
| `calibrate_confidence.py` | Measure and fit the answer-confidence score |
| `chat_diag.py` | Show routing decision, row count and answer for one query |
| `export_onnx_models.py` | Export Brain models to ONNX and verify parity |
| `fix_future_dated_rows.py` | One-off: shift future-dated seed rows back one year |
| `g4_battery.py` | QuickML LLM contract test battery |
| `get_refresh_token.py` | One-time Zoho OAuth grant-code exchange |
| `load_test.py` | Load test [INFERRED from name; no docstring] |
| `make_clean_copy.py` | Export a clean runnable copy of the backend |
| `measure_footprint.py` | Measure disk and RAM cost of the backend |
| `mint_token.py` | Mint a signed bearer token |
| `obs_judge_worker.py` | Offline judge worker for traces [INFERRED from name] |
| `quickml_ping.py` | Measure QuickML endpoint success rate |
| `quickml_token_test.py` | Test getting a QuickML token from `.env` alone |
| `rebuild_db.py` | Rebuild `main.db` onto fresh storage |
| `replant_p2.py` | Re-anchor a planted demo spike to the current week |
| `run_eval.py` | Run the eval suite [INFERRED from name] |
| `set_password.py` | Create an officer account or change its password |
| `train_backend.py` | [INFERRED from name only; no docstring] |

Scripts found: 25. Documented: 25.

## 0.5 Environment variables

Plain English: these are the switches and keys the build reads
at start-up. Only names are shown. Secret values are masked.

`.env` is read by pydantic-settings
(`app/core/settings.py:28`). The local `.env` sets 39 names.
`.env.example` lists 47 names.

### 0.5.1 Settings fields (54) - `app/core/settings.py:27-127`

| Name | Default | Controls | Read at |
|---|---|---|---|
| `CATALYST_PROJECT_ID` | empty | Catalyst project identity | `app/core/catalyst.py`, `second_brain/store.py` |
| `CATALYST_PROJECT_SECRET` | **** | Catalyst credential | `app/core/catalyst.py` |
| `CATALYST_PROJECT_KEY` | **** | Catalyst credential | `app/core/catalyst.py` |
| `CATALYST_ENV` | `development` | `production` turns on fail-closed security | `app/core/security.py` |
| `STRATUS_BUCKET_NAME` | `antar-files` | Object-storage bucket name | `app/core/catalyst.py`, `services/stratus.py` |
| `QUICKML_CLIENT_ID` | **** | LLM OAuth client; also decides "LLM on" | `main.py:276`; 11 files |
| `QUICKML_CLIENT_SECRET` | **** | LLM OAuth secret | `main.py:276`; 8 files |
| `QUICKML_LLM_MODEL` | `Qwen-3.6-Instruct` | Base model name | No reader found (F0-14) |
| `QUICKML_CHAT_MODEL` | `GLM-4.7-Flash` | Fast chat model name | `services/quickml.py`, `obs/judge.py`, `obs/eval.py` |
| `QUICKML_DEFAULT_MODEL` | `Qwen-3.6-35B` | Analytical model name | `services/quickml.py` |
| `QUICKML_VISION_MODEL` | `VL-Qwen3.6-35B-A3B` | Vision model for scanned evidence | `services/quickml.py` |
| `QUICKML_LLM_MAX_TOKENS` | `4096` | Total context budget | `services/quickml.py` |
| `QUICKML_LLM_TEMPERATURE` | `0.3` | Sampling temperature | `services/quickml.py` |
| `QUICKML_LLM_ENDPOINT_URL` | empty | LLM endpoint | `services/quickml.py`, `main.py:279` |
| `QUICKML_CHAT_ENDPOINT_URL` | empty | Chat-model endpoint | `services/quickml.py`, `main.py:279` |
| `QUICKML_VISION_ENDPOINT_URL` | empty | Vision endpoint | `services/quickml.py` |
| `QUICKML_ORG_ID` | empty | Zoho org header value | `services/quickml.py` |
| `QUICKML_TOKEN_URL` | Zoho accounts token URL | OAuth token endpoint | `services/quickml.py` |
| `QUICKML_SCOPE` | `QuickML.deployment.READ` | OAuth scope | `services/quickml.py` |
| `QUICKML_AUTH_MODE` | `oauth` | `oauth`, `apikey` or `none` | `services/quickml.py` |
| `QUICKML_SOID` | empty | Scope-owner id | `services/quickml.py` |
| `QUICKML_ACCESS_TOKEN` | **** | Pre-supplied token | `services/quickml.py` |
| `QUICKML_API_KEY` | **** | Direct API key | `services/quickml.py` |
| `QUICKML_REFRESH_TOKEN` | **** | Refresh-token grant | `services/quickml.py` |
| `ANTAR_EVENT_FEED_URL` | public holiday iCal URL | Festival dates for the forecast | `services/events.py:108` |
| `CRON_SECRET_KEY` | placeholder string | Shared secret for cron endpoints | `core/auth_middleware.py:189-200`, `core/security.py:284` |
| `VAPID_PUBLIC_KEY` | empty | Push-notification key | No reader found (F0-14) |
| `VAPID_PRIVATE_KEY` | **** | Push-notification key | No reader found (F0-14) |
| `VAPID_EMAIL` | example mailto | Push contact | No reader found (F0-14) |
| `BHASHINI_API_KEY` | **** | Bhashini speech/translate API | `api/voice.py`, `services/bhashini.py` |
| `BHASHINI_USER_ID` | empty | Bhashini user id | `api/voice.py`, `services/bhashini.py` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allow-list (comma separated) | `main.py:362`, `core/auth_middleware.py:233` |
| `DEMO_MODE` | `False` | Forces offline scripted answers | `api/chat.py:75,97`; 7 files |
| `APP_PORT` | `8000` | Local port | `run.py:28` (via `os.environ`) |
| `PROMPT_VERSION` | `v1` | Label stored with traces and evals | `api/chat.py:208`, `obs/eval.py:26` |
| `BRAIN_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Which embedding model loads | `second_brain/embedder.py`, `main.py:114` |
| `BRAIN_COSINE_TOP_K` | `5` | Brain result count | No reader found (F0-14) |
| `BRAIN_SIMILARITY_THRESHOLD` | `0.60` | Brain match cut-off | No reader found (F0-14) |
| `LOG_LEVEL` | `INFO` | Log verbosity | No reader found (F0-14) |
| `ANTAR_ENV` | `development` | `production` = fail-closed posture | `core/security.py` |
| `ANTAR_AUTH_SECRET` | **** | Signs login tokens; empty = header identity | `core/auth_middleware.py` |
| `ANTAR_TOKEN_TTL_S` | `28800` (8 hours) | Token lifetime | `api/auth_api.py`, `core/auth_middleware.py` |
| `ANTAR_USERS` | empty | Accounts as inline JSON (hashes) | `core/accounts.py:60` |
| `ANTAR_USERS_FILE` | `auth_users.json` | Accounts file path | `core/accounts.py` |
| `ANTAR_TRUSTED_PROXY_HOPS` | `1` | How many proxies to trust for client IP | `core/rate_limiter.py` |
| `ANTAR_MAX_BODY_MB` | `12` | Request-body size ceiling | `core/security.py` |
| `ANTAR_EXPOSE_DOCS` | `False` | Force `/docs` on in production | `main.py:343` |
| `OBS_ENABLED` | `True` | Observability master switch | `main.py:302`, `obs/judge.py:13` |
| `OBS_DIR` | `data_sessions/obs` | Where trace data is written | `obs/config.py` |
| `OBS_JUDGE_SAMPLE` | `0.05` | Share of traces sent to the judge | `obs/metrics.py:9` |
| `OBS_JUDGE_ENABLED` | `True` | Turn judge spend off | `obs/judge.py:13`, `obs/flags.py:23` |
| `OBS_COST_PER_1K` | `0.0` | Cost per 1k tokens for the cost column | `obs/metrics.py:6` |
| `OBS_SPIKE_K` | `2.0` | Spike threshold multiplier | `obs/flags.py:27` |
| `OBS_JSONL_MAX_MB` | `64` | Rotate the span log past this size | `obs/writer.py:9` |

Settings fields found: 54. Documented: 54.

### 0.5.2 Variables read directly from the environment (23)

| Name | Default | Controls | Read at |
|---|---|---|---|
| `ANTAR_DB` | `main.db` | Database file path | `app/core/db_path.py:52` |
| `X_ZOHO_CATALYST_LISTEN_PORT` | unset | Port on Catalyst; its presence means "on Catalyst" | `run.py:26`, `app/core/db_path.py:63` |
| `PORT` | unset | Fallback port | `run.py:27` |
| `ANTAR_BRAIN_ONLINE` | unset | `1` allows a model download | `main.py:22`, `second_brain/embedder.py:22` |
| `HF_HUB_OFFLINE` | set to `1` | Stops Hugging Face network calls | `main.py:23` |
| `TRANSFORMERS_OFFLINE` | set to `1` | Same, for transformers | `main.py:24` |
| `OMP_NUM_THREADS` | set to `1` if none set | Maths-library thread cap | `main.py:42-45` |
| `OPENBLAS_NUM_THREADS` | set to `1` if none set | Same | `main.py:42-45` |
| `MKL_NUM_THREADS` | set to `1` if none set | Same | `main.py:42-45` |
| `ANTAR_BRAIN_BACKEND` | `auto` | `onnx`, `torch` or auto-pick | `second_brain/embedder.py:73`, `reranker.py:59` |
| `ANTAR_BRAIN_DB` | unset | Override vector-store path | `second_brain/vec_store.py:79` |
| `ANTAR_ONNX_DIR` | `models/onnx` | Where ONNX models live | `second_brain/onnx_backend.py:36` |
| `ANTAR_ONNX_THREADS` | `0` (auto, min 1) | ONNX thread count | `second_brain/onnx_backend.py:55` |
| `ANTAR_CHECKPOINT` | `sqlite` | `sqlite` or `memory` case file | `agents/checkpoint_store.py:414` |
| `ANTAR_CHECKPOINT_DB` | `<OBS_DIR>/case_file.db` | Case-file path | `agents/checkpoint_store.py:107` |
| `ANTAR_SESSION_KEY` | unset | Fernet key for saved sessions; else `.session_key` file | `api/session_api.py:64` |
| `ANTAR_FORECAST_AS_OF` | `wallclock` | Date the forecast is anchored to | `forecast/asof.py:23,65` |
| `ANTAR_FORECAST_NEAR_REPEAT` | `0` | Turn the near-repeat feature on | `forecast/features.py:66` |
| `ANTAR_INTENT_TIMEOUT_S` | `6` | Intent-parser LLM timeout | `agents/intent_parser.py:228` |
| `ANTAR_SELECT_TIMEOUT_S` | `8` | Routing LLM timeout | `agents/query_agent.py:43` |
| `QUICKML_BUDGET_S` | `20` (min 2) | Per-question LLM time budget | `services/quickml.py:151` |
| `SELF_HEAL_CORPUS_MAX` | `40000` | Row cap for the fallback search index | `services/hybrid_index.py:31` |
| `USE_LOCAL` | `1` | Use the local SQLite executor | `services/zcql_local.py:13` |

Also: `MODEL_PATH` (`tools/local_intent_classifier.py:27`,
local LLM file, absent), `PYTEST_CURRENT_TEST`
(`services/quickml.py:144`, set by pytest, disables the circuit
breaker in tests), `HF_HOME` and `TOKENIZERS_PARALLELISM`
(`Dockerfile:16-17`, read by libraries).

Base64 workaround: five names may be supplied as `<NAME>_B64`
because the Catalyst console rejects values starting with a
digit. They are decoded before settings load
(`app/core/settings.py:11-24`): `QUICKML_CLIENT_ID`,
`QUICKML_CLIENT_SECRET`, `QUICKML_REFRESH_TOKEN`,
`QUICKML_ACCESS_TOKEN`, `ANTAR_SESSION_KEY`. [VERIFIED]

### 0.5.3 Frontend variables (4)

| Name | Controls | Read at |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `lib/api.js:4`; 28 read sites in 27 files |
| `NEXT_PUBLIC_BASE_PATH` | Asset path prefix | `lib/assets.js:16` |
| `NEXT_PUBLIC_DEMO_PW_ADMIN` | Demo sign-in password, value masked | `app/(auth)/login/page.jsx:210-211` |
| `NEXT_PUBLIC_DEMO_PW_APPROVER` | Demo sign-in password, value masked | `app/(auth)/login/page.jsx:185-186` |

Any `NEXT_PUBLIC_` value is compiled into the browser bundle.
See F0-3.

Environment variables found: 54 + 23 + 4 extras + 4 frontend
= 85. Documented: 85. (The five `_B64` aliases are alternate
spellings of names already counted.)

## 0.6 Counts

All counts are static (files on disk, `ast` parse, regex).
Nothing was executed.

| Thing | Count | How counted |
|---|---|---|
| Files, Antar-owned | 880 | All files minus tool folders, `gstack` (2,597), `graphify-out` (440), frontend `out/` (78), and the SQLite sidecars noted in the header |
| Git-tracked files | 1,220 | `git ls-files` |
| Backend Python files (`app/`) | 185 | 39,733 lines |
| Backend functions and methods (`app/`) | 1,402 | `ast` FunctionDef + AsyncFunctionDef |
| Backend classes (`app/`) | 109 | `ast` ClassDef |
| Router modules | 44 | `app/api/*.py` with at least one route |
| Router modules mounted | 42 | `main.py:401-449` |
| Route decorators | 179 | `@router.<method>` in `app/api` |
| Unique endpoints, mounted | 158 | method + path, trailing-slash twins folded |
| - of which GET / POST / DELETE / WebSocket | 115 / 40 / 2 / 1 | same |
| Unique endpoints, unmounted | 6 | `admin_data.py` (2), `advocate_agent_api.py` (4) |
| Frontend page files | 24 | `page.jsx` under `antar-frontend/app` |
| Frontend layouts | 3 | `layout.jsx` |
| Frontend components | 52 | 51 in `components/` + `PredictScreen.jsx` |
| Frontend lib modules | 13 | `lib/*.js`, `lib/brand.ts` |
| Frontend source lines | 30,496 | `.js`, `.jsx`, `.css`, `.ts` in app, components, lib, client |
| `onClick` handlers | 371 | regex over app, components, lib |
| `<button` elements | 314 | regex |
| `onChange` / `onKeyDown` / `onSubmit` | 59 / 17 / 2 | regex |
| `<input` / `<select` / `<textarea` / `<form` | 29 / 19 / 5 / 2 | regex |
| `fetch(` call sites | 99 | regex |
| `setInterval` timers | 19 | regex |
| `addEventListener` | 43 | regex |
| SQLite files with data | 9 | see 0.6.1 (plus 1 gzip snapshot) |
| Tables in `main.db` | 57 | includes `sqlite_sequence` |
| Views / indexes in `main.db` | 1 / 56 | view is `crimes` |
| Background workers (backend) | 9 | see 0.7 |
| Test files | 106 | `tests/test_*.py` |
| Test functions | 1,117 | `def test_*` in `tests/` (parametrised cases not expanded) |
| Declared agents | 20 | `AGENTS.md` yaml blocks (`agent:` key) |
| Graph nodes | 10 | `AGENTS.md` topology block |

The interactive-element counts are raw regex hits. The exact
per-page element inventory is Pass 4.

### 0.6.1 Database files

| File | Size | Tables | Role |
|---|---|---|---|
| `main.db` | 1.48 GB | 57 (+1 view, 56 indexes) | Live registry; `.env` points `ANTAR_DB` here; WAL mode |
| `main.db.gz` | 87.5 MB | - | Deploy snapshot, dated 2026-09-18 (`db_path.py:128-137`) |
| `data/main.db` | 1.50 GB | 57 (+1 view, 57 indexes) | Second copy, not the configured path (F0-11) |
| `brain_vectors.db` | 85.6 MB | 1 | Second Brain vector store |
| `data/brain_vectors.db` | 85.6 MB | 1 | Same size as the root copy (F0-11) |
| `intelligent.db` | 1.2 MB | 2 (`FIRs`, `question_bank`) | Question bank; role confirmed in Pass 7 |
| `data_sessions/obs/obs.db` | 4.7 MB | 10 | Live trace store (`OBS_DIR`) |
| `data_sessions/obs/case_file.db` | 41.5 MB | 2 (`checkpoints`, `checkpoint_writes`) | Live LangGraph case file |
| `data/obs/obs.db` | 1.4 MB | 10 | Older copy |
| `data/obs/case_file.db` | 11.2 MB | 2 | Older copy |

The 57 tables in `main.db`: `Act`, `ArrestSurrenderType`,
`BloodGroupMaster`, `CaseCategory`, `CaseStatusMaster`,
`CasteMaster`, `Court`, `CrimeHead`, `CrimeSubHead`,
`Designation`, `District`, `Employee`, `FIRs`, `GenderMaster`,
`GravityOffence`, `Nationality`, `OccupationMaster`, `Rank`,
`ReligionMaster`, `State`, `Unit`, `UnitType`,
`agent_reasoning_logs`, `audit_log`, `baseline`,
`crime_suspects`, `crime_zone_summary`, `dim_storyline`,
`eval_cases`, `eval_runs`, `ext_entity_keys`,
`ext_schema_notes`, `ext_synthetic_identity`,
`financial_links`, `flags`, `forecast_cube`, `forecast_meta`,
`forecast_models`, `forecast_output`, `geo_units`,
`hitl_actions`, `monthly_trend`, `officer_memory`, `officers`,
`property`, `relationships`, `scores`, `sdar_groups`,
`sdar_tokens`, `sqlite_sequence`, `stations`, `suspects`,
`trace_context`, `traces`, `victims`, `year_intel`,
`zone_summary`. Fields and row counts are Pass 7.

Tables found: 57. Tables listed: 57.

## 0.7 Background work

Plain English: things the server does on its own, without a
user clicking.

| # | Worker | Trigger | Where | Real or mock |
|---|---|---|---|---|
| 1 | Background warm-up | Once at boot | `main.py:93-310`, started `main.py:328` | [VERIFIED] real |
| 2 | Dispatch simulator | Loop from boot | `main.py:323-324`, `app/api/live_stream.py:45,70` | [STUB/MOCK] simulated feed by its own name; detail Pass 5 |
| 3 | Orchestrator loop | Every 60 s | `main.py:297`, `app/core/orchestrator.py:197-231` | [VERIFIED] refreshes expiring products, runs the sentinel scan |
| 4 | Long-task jobs | One task per job request | `app/api/jobs.py:244` | [VERIFIED] exists; detail Pass 5 |
| 5 | Forecast daemon threads | On demand | `app/forecast/service.py:176`, `:376` | [VERIFIED] exists; detail Pass 8 |
| 6 | Chat stream pipeline task | Per streamed question | `app/core/sse.py:44`, `app/api/chat_stream.py:761` | [VERIFIED] exists |
| 7 | Cron endpoint: alert scan | `POST /api/alerts/scan` with `X-Cron-Secret` | `app/api/alerts.py:50-51` | Endpoint real; the scheduler that calls it is [NOT FOUND] in the repo |
| 8 | Cron endpoint: brain consolidate | `POST /api/brain/consolidate` with `X-Cron-Secret` | `app/api/brain.py:42-43` | Same |
| 9 | `TaskWorker` queue | Never started | `app/core/worker.py:12-57` | [STUB/MOCK] no importer found |

Also unreachable: a `BackgroundTasks` job in
`app/api/admin_data.py:183`, because that router is not mounted.

The warm-up (worker 1) runs 20 steps in order. 19 are wrapped
in `try/except`, so a failure prints a warning and the boot
continues. The LLM warm-up call is the one step not wrapped
(`main.py:279-291`); whether it can raise is checked in Pass 6.
The steps (`main.py:101-308`): stage database, load embedder, rebuild
Brain index, seed demo Brain if empty, index MO fields, graph
cache, district cache, evidence ledger + default products +
memory DB, reranker, dataset overview, dataset summary, officer
view, crime-graph cycles per year, Gi* surface, forecast cube
and forecasts, forecast scan, query warm-up (templates T22, T23,
T11, T13, T17), LLM warm-up, orchestrator start, observability
DB. [VERIFIED]

Frontend: 19 `setInterval` timers exist. Each is traced to its
page in Pass 4.

Background workers found: 9. Documented: 9.

## 0.8 Problems flagged in this pass

No fixes were applied. Severity is a first estimate; Pass 10
ranks security items properly.

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| F0-1 | No `next.config.*`. The static export in `out/` is dated 2026-09-15 and has no `/approvals` page, though `app/(app)/approvals/page.jsx` exists | `antar-frontend/out/` listing; `antar-frontend/catalyst.json` | The frontend deploy folder cannot be rebuilt as-is and is missing the HITL approvals screen |
| F0-2 | `.env.production` sets `NEXT_PUBLIC_API_URL` to `http://127.0.0.1:8000`. The comment in `lib/api.js:3` says "Hardcoded for production" but the code reads the env var | `antar-frontend/.env.production:1`, `lib/api.js:3-4` | A production build would call the visitor's own machine |
| F0-3 | Demo passwords are read from `NEXT_PUBLIC_` variables, which ship to every browser | `app/(auth)/login/page.jsx:185-186,210-211`; `.env.local` comment line 2 warns of this | Anyone opening a build made with `.env.local` can read the passwords |
| F0-4 | Tailwind config and `@tailwind` directives exist, but `tailwindcss` is not installed and there is no PostCSS config | `tailwind.config.js:1-36`, `app/globals.css:1-3` | Tailwind utility classes are not generated [INFERRED]; styling relies on the hand-written stylesheet |
| F0-5 | Two routers are never mounted: `admin_data.py` (2 routes) and `advocate_agent_api.py` (4 routes). `AGENTS.md` cites `GET /api/advocate-agent/base-rates`; the mounted path is `/api/adversarial-audit/base-rates` | `main.py:401-449`, `app/api/adversarial_audit_api.py:64`, `main.py:442` | 6 endpoints are unreachable; the manifest names a path that returns 404 |
| F0-6 | `app/agents/chat_stream.py` is a 769-line near-copy of `app/api/chat_stream.py` with no importer | file hashes differ; import scan | Dead duplicate; an edit to the wrong copy changes nothing |
| F0-7 | Modules with no importer in `app/` or `main.py`: `app/config/prompt_loader.py`, `app/core/evaluator.py`, `app/core/worker.py`, `app/graph/intent_flow.py`, `app/services/forensics.py`, `app/services/stratus.py`, `app/services/push.py` (4 lines), `app/services/smartbrowz.py` (4 lines), `app/tools/registry.py` | static import scan [INFERRED; dynamic imports are confirmed in Pass 6] | Dead-code candidates |
| F0-8 | `main.py:3` says Python 3.12; the runtime is 3.11 | `Dockerfile:1`, `app-config.json:3`, `RUN.md:30-31` | Stale header comment |
| F0-9 | Embedding model differs by environment: default and container say `BAAI/bge-small-en-v1.5`; the local `.env` says `all-MiniLM-L6-v2` | `settings.py:87`, `Dockerfile:20`, `app-config.json:13`, `.env` | Local and deployed Brain may embed with different models; checked in Pass 8 |
| F0-10 | **Fixed 2026-10-22** (quickml.py names the models from settings). Model names disagreed: `QUICKML_DEFAULT_MODEL` default is `Qwen-3.6-35B`, local `.env` says `Qwen-3.6-Instruct`; `quickml.py:1-3` docstring says "Qwen 2.5 14B" | `settings.py:48`, `.env`, `app/services/quickml.py:1-3` | The model named on stage must match the one actually called |
| F0-11 | Two full database copies: `main.db` (configured) and `data/main.db` (larger, one more index). Two `obs` folders. `main.db.gz` is dated 2026-09-18, older than `main.db` (2026-10-13) | 0.6.1; `db_path.py:128-137`; the size comment at `db_path.py:60-62` ("~46 MB vs 276 MB") is also out of date | The deploy snapshot may not match the local data [INFERRED from timestamps] |
| F0-12 | `run.py:5-11` defines `install_dependencies()` and never calls it | `run.py:5-11` | Dead code |
| F0-13 | `Dockerfile.onnx` says "NOT YET BUILT"; the torch `Dockerfile` is the stated working deploy path, while the local venv is torch-free | `Dockerfile.onnx:3-9`, `RUN.md:8-14` | Local runs and the deployed image use different model runtimes |
| F0-14 | Settings with no reader found: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL`, `LOG_LEVEL`, `BRAIN_COSINE_TOP_K`, `BRAIN_SIMILARITY_THRESHOLD`, `QUICKML_LLM_MODEL` | name search over `app/`, `main.py`, `run.py` | Push notifications look unimplemented [STUB/MOCK]; the others are unused knobs |
| F0-15 | `CRON_SECRET_KEY` has a known placeholder default | `settings.py:66`; refused in production at `core/security.py:284-286` | Safe only when `ANTAR_ENV` or `CATALYST_ENV` is `production` |
| F0-16 | Three `.rej` patch leftovers in frontend source | `app/(app)/profiles/page.jsx.rej`, `components/MapView.jsx.rej`, `components/NetworkGraph.jsx.rej` | Rejected patch hunks; show edits that did not apply |
| F0-17 | No git remote and no CI | `git remote -v`; no `.github/` | Tests run only by hand; no off-machine backup of history |
| F0-18 | `RUN.md:107-115` says the frontend lives on `E:\Antar_FinalBuild_Dev`; `.claude/launch.json` uses `D:\Project\antar-frontend` | both files | Doc drift |
| F0-19 | `antar-frontend/client/` is an untouched "testApp / Hello World" scaffold | `client/index.html`, `client/client-package.json` | [STUB/MOCK]; not the real client |
| F0-20 | A "dispatch simulator" starts at every boot | `main.py:322-325` | Simulated live feed; must be described as such in the demo |
| F0-21 | `public/fir_synthetic.csv` (1.2 MB) is served as a public static file | `antar-frontend/public/` | Synthetic FIR data is downloadable from the site root |
| F0-22 | Tests were not run for this document. The suite edits the live `main.db` | `RUN.md:102-105` | Pass/fail status of the 1,117 tests is not verified in this document |
| F0-23 | `run_update4.py` does not parse (syntax error) | `ast` parse | Scratch script only; excluded from deploys |
| F0-24 | Unused frontend dependencies: `maplibre-gl`, `hls.js`, `animate.css` | import scan over app, components, lib | Extra install weight [INFERRED] |

Problems flagged: 24.

## 0.9 Pass 0 count report

| Inventory | Found | Documented |
|---|---|---|
| Folders (3 levels, excl. gstack internals) | 81 | 81 |
| Root files | 71 | 71 |
| Backend runtime libraries | 24 | 24 |
| Frontend libraries | 21 | 21 |
| Entry points | 11 | 11 |
| Scripts in `scripts/` | 25 | 25 |
| Environment variables | 85 | 85 |
| Database files with data (9 SQLite + 1 gzip) | 10 | 10 |
| Tables in `main.db` | 57 | 57 (names; fields in Pass 7) |
| Background workers | 9 | 9 |
| Problems flagged | 24 | 24 |

Counted here, documented in later passes:

| Inventory | Found | Documented in |
|---|---|---|
| Page files | 24 | Pass 3, Pass 4 |
| Components | 52 | Pass 4 |
| Unique mounted endpoints | 158 | Pass 5 |
| Backend functions and methods | 1,402 | Pass 6 |
| Test functions | 1,117 | Pass 11, Pass 13 |

PASS 0 done.
