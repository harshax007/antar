"""
Patch remaining today() call sites with clock.today().
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

def patch_file(rel_path: str, old_str: str, new_str: str):
    p = ROOT / rel_path
    with open(p, "rb") as f:
        content = f.read()
    
    old_bytes_lf = old_str.replace("\r\n", "\n").encode("utf-8")
    old_bytes_crlf = old_str.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    
    is_crlf = b"\r\n" in content
    new_bytes = (new_str.replace("\r\n", "\n").replace("\n", "\r\n") if is_crlf else new_str.replace("\r\n", "\n")).encode("utf-8")
    
    if old_bytes_crlf in content:
        content = content.replace(old_bytes_crlf, new_bytes, 1)
        with open(p, "wb") as f:
            f.write(content)
        print(f"Patched (CRLF): {rel_path}")
        return True
    elif old_bytes_lf in content:
        content = content.replace(old_bytes_lf, new_bytes, 1)
        with open(p, "wb") as f:
            f.write(content)
        print(f"Patched (LF): {rel_path}")
        return True
    else:
        print(f"FAILED to find target in: {rel_path}")
        return False

# 1. app/services/zcql_repo.py _today_cap
old_cap = """def _today_cap() -> str:
    \"\"\"Upper date bound for queries on the raw FIRs table. _bound_to_today only guards the
    `crimes` view, and the data holds future-dated rows (up to 2026-12-31).\"\"\"
    return date.today().isoformat() + " 23:59\""""

new_cap = """def _today_cap() -> str:
    \"\"\"Upper date bound for queries on the raw FIRs table. _bound_to_today only guards the
    `crimes` view, and the data holds future-dated rows (up to 2026-12-31).\"\"\"
    from app.core import clock
    return clock.today().isoformat() + " 23:59\""""
patch_file("app/services/zcql_repo.py", old_cap.strip(), new_cap.strip())

# 2. app/core/date_guard.py redact_future_dates
old_dg = """def redact_future_dates(obj: Any, today: date | None = None) -> Any:
    \"\"\"Deep-copy *obj* with any future calendar date scrubbed.

    A string that IS a bare future date becomes None; a string that merely
    CONTAINS one gets the date replaced with 'upcoming'.
    \"\"\"
    today = today or date.today()"""

new_dg = """def redact_future_dates(obj: Any, today: date | None = None) -> Any:
    \"\"\"Deep-copy *obj* with any future calendar date scrubbed.

    A string that IS a bare future date becomes None; a string that merely
    CONTAINS one gets the date replaced with 'upcoming'.
    \"\"\"
    from app.core import clock
    today = today or clock.today()"""
patch_file("app/core/date_guard.py", old_dg.strip(), new_dg.strip())

# 3. app/agents/query_agent.py _bound_to_today
old_qa = """    if getattr(spec, "table", None) != "crimes":
        return
    from datetime import date as _date
    spec.filters.append(Filter("occurred_at", "<=", f"{_date.today().isoformat()} 23:59"))"""

new_qa = """    if getattr(spec, "table", None) != "crimes":
        return
    from app.core import clock
    spec.filters.append(Filter("occurred_at", "<=", f"{clock.today().isoformat()} 23:59"))"""
patch_file("app/agents/query_agent.py", old_qa.strip(), new_qa.strip())

# 4. app/agents/answer_writer.py
old_aw = """    import calendar
    from app.services.zcql_repo import real_data_today
    out: set[str] = set()
    for anchor in (date.today(), real_data_today()):"""

new_aw = """    import calendar
    from app.services.zcql_repo import real_data_today
    from app.core import clock
    out: set[str] = set()
    for anchor in (clock.today(), real_data_today()):"""
patch_file("app/agents/answer_writer.py", old_aw.strip(), new_aw.strip())

old_aw2 = """    cut = _partial_months()
    cur = date.today().strftime("%Y-%m")"""

new_aw2 = """    cut = _partial_months()
    from app.core import clock
    cur = clock.today().strftime("%Y-%m")"""
patch_file("app/agents/answer_writer.py", old_aw2.strip(), new_aw2.strip())
