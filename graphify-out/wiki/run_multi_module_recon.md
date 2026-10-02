# run_multi_module_recon

> 37 nodes · cohesion 0.08

## Key Concepts

- **run_multi_module_recon()** (11 connections) — `app/services/osint_recon.py`
- **osint_recon.py** (10 connections) — `app/services/osint_recon.py`
- **osint_api.py** (9 connections) — `app/api/osint_api.py`
- **osint.py** (8 connections) — `app/services/osint.py`
- **search_osint()** (8 connections) — `app/services/osint.py`
- **test_layer5_search_osint.py** (8 connections) — `tests/test_layer5_search_osint.py`
- **get_osint_recon()** (5 connections) — `app/api/osint_api.py`
- **test_osint.py** (5 connections) — `tests/test_osint.py`
- **osint_agent.py** (4 connections) — `app/agents/osint_agent.py`
- **get_osint()** (4 connections) — `app/api/osint_api.py`
- **_run_maltego_linkage_module()** (4 connections) — `app/services/osint_recon.py`
- **_run_phone_infoga_module()** (4 connections) — `app/services/osint_recon.py`
- **Any** (3 connections)
- **_run_osint_corroboration()** (3 connections) — `app/services/osint_recon.py`
- **_run_sherlock_module()** (3 connections) — `app/services/osint_recon.py`
- **test_multi_module_recon_and_quarantine()** (3 connections) — `tests/test_layer5_search_osint.py`
- **test_suggest_identity_links()** (3 connections) — `tests/test_layer5_search_osint.py`
- **test_search_osint()** (3 connections) — `tests/test_osint.py`
- **get** (2 connections)
- **Antar — OSINT Agent (A6) ============================= Agent responsible for…** (1 connections) — `app/agents/osint_agent.py`
- **Antar — OSINT API (Phase 6) ================================ Endpoints for the…** (1 connections) — `app/api/osint_api.py`
- **Returns unverified open-web claims and risk flags for the given entity.** (1 connections) — `app/api/osint_api.py`
- **Layer 5 Multi-Module Reconnaissance Endpoint. Returns: • Maltego Linkage Graph…** (1 connections) — `app/api/osint_api.py`
- **Antar — OSINT Service (Phase 6) ==================================== Open-web…** (1 connections) — `app/services/osint.py`
- **Searches DuckDuckGo HTML for the entity name. Extracts the first 3 results as…** (1 connections) — `app/services/osint.py`
- *... and 12 more nodes in this community*

## Relationships

- [typing](typing.md) (5 shared connections)
- [pytest](pytest.md) (3 shared connections)
- [profile.py](profile.py.md) (3 shared connections)
- [jobs.py](jobs.py.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `app/agents/osint_agent.py`
- `app/api/osint_api.py`
- `app/services/osint.py`
- `app/services/osint_recon.py`
- `tests/test_layer5_search_osint.py`
- `tests/test_osint.py`

## Audit Trail

- EXTRACTED: 67 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*