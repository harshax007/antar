# scan

> 17 nodes · cohesion 0.14

## Key Concepts

- **scan()** (19 connections) — `app/agents/forecast_agent.py`
- **inject_intelligence.py** (9 connections) — `app/seeds/inject_intelligence.py`
- **inject_evidence_syndicates.py** (8 connections) — `app/seeds/inject_evidence_syndicates.py`
- **_brain_context()** (4 connections) — `app/agents/forecast_agent.py`
- **get_week_dates()** (4 connections) — `app/seeds/inject_intelligence.py`
- **scan_alerts()** (3 connections) — `app/api/alerts.py`
- **inject()** (3 connections) — `app/seeds/inject_intelligence.py`
- **replace_all()** (3 connections) — `app/services/alerts_store.py`
- **test_warning_ledger_provenance_persistence()** (3 connections) — `tests/test_layer3_predictive_warnings.py`
- **inject_evidence()** (2 connections) — `app/seeds/inject_evidence_syndicates.py`
- **Best-effort `resolved_pattern` match for an alert (the WOW-3 brain context).…** (1 connections) — `app/agents/forecast_agent.py`
- **Run the scan → alerts. Returns {created, alerts}. Idempotent (replaces the…** (1 connections) — `app/agents/forecast_agent.py`
- **post** (1 connections)
- **Antar — Non-Cyber Evidence & Syndicate Data Injection…** (1 connections) — `app/seeds/inject_evidence_syndicates.py`
- **Antar — Multi-Dimensional Crime Intelligence Data Injection…** (1 connections) — `app/seeds/inject_intelligence.py`
- **Return dates falling in trailing week `week_idx` (0 = days 0..6 from REF_DATE).** (1 connections) — `app/seeds/inject_intelligence.py`
- **A scan recomputes the whole picture, so replace the set (idempotent re-scan).** (1 connections) — `app/services/alerts_store.py`

## Relationships

- [typing](typing.md) (5 shared connections)
- [time](time.md) (4 shared connections)
- [anomaly.py](anomaly.py.md) (3 shared connections)
- [app_services](app_services.md) (3 shared connections)
- [sys](sys.md) (2 shared connections)
- [obs/store.py](obs-store.py.md) (2 shared connections)
- [semantic_recall](semantic_recall.md) (1 shared connections)
- [jobs.py](jobs.py.md) (1 shared connections)
- [trace.py](trace.py.md) (1 shared connections)
- [dataset.py](dataset.py.md) (1 shared connections)
- [alert_suggest_agent.py](alert_suggest_agent.py.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/agents/forecast_agent.py`
- `app/api/alerts.py`
- `app/seeds/inject_evidence_syndicates.py`
- `app/seeds/inject_intelligence.py`
- `app/services/alerts_store.py`
- `tests/test_layer3_predictive_warnings.py`

## Audit Trail

- EXTRACTED: 46 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*