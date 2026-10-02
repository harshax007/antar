# redact_future_dates

> 33 nodes · cohesion 0.09

## Key Concepts

- **redact_future_dates()** (18 connections) — `app/core/date_guard.py`
- **test_prediction_privacy.py** (13 connections) — `tests/test_prediction_privacy.py`
- **find_future_dates()** (12 connections) — `app/core/date_guard.py`
- **date_guard.py** (8 connections) — `app/core/date_guard.py`
- **TestBoard** (8 connections) — `tests/test_prediction_privacy.py`
- **TestDateGuard** (6 connections) — `tests/test_prediction_privacy.py`
- **_dates_in()** (4 connections) — `app/core/date_guard.py`
- **walk()** (4 connections) — `app/core/date_guard.py`
- **scrub()** (4 connections) — `app/core/date_guard.py`
- **TestEndpoints** (4 connections) — `tests/test_prediction_privacy.py`
- **board()** (3 connections) — `tests/test_prediction_privacy.py`
- **anyio** (3 connections)
- **.test_board_endpoint_has_no_future_dates()** (3 connections) — `tests/test_prediction_privacy.py`
- **.test_forecast_endpoint_has_no_future_dates()** (3 connections) — `tests/test_prediction_privacy.py`
- **.test_scenario_endpoint_has_no_future_dates()** (3 connections) — `tests/test_prediction_privacy.py`
- **Any** (2 connections)
- **.test_limit_respected()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_no_future_dates_anywhere()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_finds_future_dates()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_ignores_past_and_today()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_preserves_everything_else()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_redacts_bare_future_date()** (2 connections) — `tests/test_prediction_privacy.py`
- **.test_redacts_embedded_future_date()** (2 connections) — `tests/test_prediction_privacy.py`
- **Antar — Future-Date Guard ============================== Policy: future-date…** (1 connections) — `app/core/date_guard.py`
- **Return every ISO date string strictly after *today* found in obj.** (1 connections) — `app/core/date_guard.py`
- *... and 8 more nodes in this community*

## Relationships

- [typing](typing.md) (8 shared connections)
- [pattern_predict.py](pattern_predict.py.md) (5 shared connections)
- [_date](_date.md) (3 shared connections)
- [anomaly.py](anomaly.py.md) (3 shared connections)
- [pytest](pytest.md) (2 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `app/core/date_guard.py`
- `tests/test_prediction_privacy.py`

## Audit Trail

- EXTRACTED: 72 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*