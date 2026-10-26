"""One crime filter for the Map, the same one the chat uses.

The register spells a crime type several ways: the 10-lakh FIRs in capitals ("THEFT",
"BURGLARY - NIGHT", " CYBER CRIME"), the demonstration rows as keys ("theft",
"chain_snatching"), and vehicle theft and chain snatching live in sub-headings
(CrimeHead_Name) under THEFT and ROBBERY. The Map's pills send the key. It used to be
compared with `crime_type` as is, so "Theft" found the 34 demonstration rows in a month
and missed the 155 register FIRs, and "Vehicle theft" found only demonstration rows.

`crime_sql` is the chat's resolution (zcql_repo) as parameterised SQL. `row_matcher`
tests the Map's in-memory rows, which carry the FIR id but no sub-heading, by the set of
FIR ids that SQL selects.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from types import SimpleNamespace
from typing import Callable, Optional


def crime_sql(crime_type: Optional[str]) -> Optional[tuple[str, list]]:
    """WHERE fragment and its arguments for one crime type, or None for all crime."""
    if not crime_type or not str(crime_type).strip():
        return None
    from app.services.zcql_repo import _crime_head_filters, normalize_crime_types
    parts, args = [], []
    for f in _crime_head_filters(SimpleNamespace(crime_types=normalize_crime_types([crime_type]), heads=[]),
                                 "crime_type", "CrimeHead_Name"):
        if f.op == "in":
            parts.append(f"UPPER(TRIM({f.column})) IN ({', '.join('?' * len(f.value))})")
            args += [str(v).strip().upper() for v in f.value]
        elif f.op == "head_or":
            heads, labels, tc = f.value
            parts.append(f"(UPPER(TRIM(CrimeHead_Name)) IN ({', '.join('?' * len(heads))}) "
                         f"OR UPPER(TRIM({tc})) IN ({', '.join('?' * len(labels))}))")
            args += [str(v).strip().upper() for v in heads] + [str(v).strip().upper() for v in labels]
    if not parts:
        # a type the resolver has no entry for (e.g. MISSING PERSON): its own spelling
        return "UPPER(TRIM(crime_type)) = ?", [str(crime_type).strip().upper()]
    return " AND ".join(parts), args


@lru_cache(maxsize=24)
def _ids(crime_type: str) -> frozenset:
    from app.core.db_path import DB_PATH, registry_connect
    where, args = crime_sql(crime_type)
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return frozenset(r[0] for r in con.execute(f"SELECT fir_id FROM FIRs WHERE {where}", args))
    except sqlite3.Error:
        return frozenset()
    finally:
        con.close()


def row_matcher(crime_type: Optional[str]) -> Callable[[dict], bool]:
    """A test for the Map's rows ({crime_id, crime_type, ...}); all rows pass with no type."""
    if not crime_type or not str(crime_type).strip():
        return lambda r: True
    ids = _ids(str(crime_type).strip())
    return lambda r: r.get("crime_id") in ids or r.get("fir_number") in ids
