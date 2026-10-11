"""
Antar - Brain console
=====================
Runs ONE agent on ONE record an officer has pointed at in the Brain screen - by dropping
the agent on a node or by typing `run <agent> <target>` - and returns the answer in the
constitution's template: bottom line, context, evidence, limits, next step.

This is a surface, not an agent. Every handler calls the entry point AGENTS.md declares
for that agent and reads its real output; nothing here computes intelligence of its own,
and nothing is returned that the agent did not produce. Three rules follow from the laws:

  - An agent that needs a suspect is REFUSED on a record with no accused - it does not
    fall back to "the nearest suspect" (law 1: never answer a different question).
  - Every result carries one evidence class, and inferences say they are inferences.
  - Nothing here acts. A patrol or a watch is proposed through HITL, never from a console.

Each card also states HOW that agent works a new problem. That text is shown to the
officer next to the result, so it describes the steps the handler below actually takes.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.core import antar_identity as identity

_CACHE_TTL_S = 300.0
_CACHE_MAX = 256
_cache: dict[tuple, tuple[float, dict]] = {}

_SUSPECT_RE = re.compile(r"^(?:S\d{3,}|ACC-[A-Z0-9-]+)$", re.I)
_FIR_REF_RE = re.compile(r"^EV-\d+$", re.I)
_KEY_RE = re.compile(r"^(vehicle|upi|ip):(.+)$", re.I)  # a hard key typed by name: upi:name@bank


# ── what the officer pointed at ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Target:
    accused: str = ""        # suspect / accused id on the record (S0041, ACC-KA-500777)
    vehicle: str = ""        # the other hard keys a record can carry. A graph node has NO
    upi: str = ""            # id the backend can use (it is numbered by its place in a
    ip: str = ""             # list), so a record is identified by what it carries.
    fir_ref: str = ""        # evidence-ledger reference (EV-12): a typed reference only
    station: str = ""        # police station (UnitName)
    district: str = ""
    crime_group: str = ""

    @property
    def label(self) -> str:
        return (self.accused or self.fir_ref or self.vehicle or self.upi or self.ip
                or self.station or self.district or self.crime_group)

    def key(self) -> tuple:
        return (self.accused, self.vehicle, self.upi, self.ip, self.fir_ref, self.station,
                self.district, self.crime_group)


def parse_target(raw: Any) -> Target:
    """A node dropped from the graph (a dict) or a word typed in the terminal (a string).

    A typed word is classified by its SHAPE only - an id that looks like a suspect is a
    suspect, anything else is taken as a place name and left for the forecast store to
    resolve or refuse. Nothing is looked up by similarity here.
    """
    if isinstance(raw, dict):
        g = lambda k: str(raw.get(k) or "").strip()
        return Target(accused=g("accused").upper(), vehicle=g("vehicle"), upi=g("upi"), ip=g("ip"),
                      station=g("station"), district=g("district"), crime_group=g("crime_group"))
    text = str(raw or "").strip().strip('"').strip("'")
    if _SUSPECT_RE.match(text):
        return Target(accused=text.upper())
    if _FIR_REF_RE.match(text):
        return Target(fir_ref=text.upper())
    if (m := _KEY_RE.match(text)):
        return Target(**{m.group(1).lower(): m.group(2).strip()})
    return Target(station=text)


# ── result helpers ───────────────────────────────────────────────────────────────

def _ok(cls: str, bottom: str, *, context: str = "", evidence: list[str] | None = None,
        limits: list[str] | None = None, nxt: list[str] | None = None) -> dict:
    return {"status": "ok", "evidence_class": cls, "bottom_line": bottom, "context": context,
            "evidence": (evidence or [])[:8], "limits": limits or [], "next": nxt or []}


def _empty(bottom: str, *, limits: list[str] | None = None, nxt: list[str] | None = None) -> dict:
    """The agent ran and the record holds nothing - an answer, stated as one."""
    return {"status": "empty", "evidence_class": "U", "bottom_line": bottom, "context": "",
            "evidence": [], "limits": limits or [], "next": nxt or []}


def _refuse(bottom: str, *, nxt: list[str] | None = None) -> dict:
    """The agent did NOT run. Says why, and what it can be run on instead."""
    return {"status": "refused", "evidence_class": None, "bottom_line": bottom, "context": "",
            "evidence": [], "limits": [], "next": nxt or []}


def _ro() -> sqlite3.Connection:
    from app.core.db_path import DB_PATH, ensure_db_staged
    ensure_db_staged()
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _in_registry(sid: str) -> bool:
    con = _ro()
    try:
        return con.execute("SELECT 1 FROM suspects WHERE suspect_id = ? LIMIT 1", (sid,)).fetchone() is not None
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()


def _need_suspect(t: Target, agent: str) -> dict | None:
    if not t.accused:
        return _refuse(f"I can't run {agent} here: this record names no accused, and I won't "
                       f"pick one for it.", nxt=["run geo", "run forecast", "run pattern"])
    if not _in_registry(t.accused):
        return _refuse(f"I can't run {agent} on {t.accused}: it is not in the suspect registry "
                       f"and is not named on any FIR in the Brain dataset.", nxt=["run linkage"])
    return None


# ── an accused id that is on FIRs but not in the suspect registry ────────────────
# The registry holds a few thousand profiled suspects (S0041). The FIRs name many more
# accused ids (ACC-KA-500777) that were never profiled: there is no name, no associate list
# and no priority factors for them. Refusing them left the agents silent about most of the
# ids an officer actually sees on a record. So for such an id each suspect agent answers
# from the FIRs that carry it - and says plainly what it could not do without a registry
# entry. Nothing is inferred to make up the difference: no score, no hypothesis.

_FIR_COLS = ("District_Name, UnitName, FIR_YEAR, FIR_MONTH, CrimeGroup_Name, CrimeHead_Name, "
             "Place_of_Offence, Vehicle_Reg_No, UPI_ID, IP_Address, Accused_ID")
_HARD_KEYS = (("Vehicle_Reg_No", "vehicle"), ("UPI_ID", "UPI"), ("IP_Address", "IP"))
_NOT_PROFILED = "is named on FIRs but is not in the suspect registry"


def _brain_con() -> sqlite3.Connection:
    """The store the Brain screen draws from: intelligent.db when present, else the registry.
    The same choice linkage_agent.brain_linkage makes, so the two cannot disagree."""
    import os
    intel = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligent.db"))
    con = sqlite3.connect(f"file:{intel}?immutable=1", uri=True) if os.path.exists(intel) else _ro()
    con.row_factory = sqlite3.Row
    return con


def _fir_rows(accused: str) -> list[sqlite3.Row]:
    """The FIRs that name this accused id, newest first. Exact match only."""
    con = _brain_con()
    try:
        return con.execute(f"SELECT {_FIR_COLS} FROM FIRs WHERE Accused_ID = ? "
                           "ORDER BY CAST(FIR_YEAR AS INT) DESC, CAST(FIR_MONTH AS INT) DESC LIMIT 500",
                           (accused,)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def _on_firs_only(t: Target) -> list[sqlite3.Row]:
    """Rows for an accused id the registry does not hold; [] when the registry has it (the
    registry path then runs) or when no FIR names it (the agent then refuses)."""
    if not t.accused or _in_registry(t.accused):
        return []
    return _fir_rows(t.accused)


def _top(rows: list[sqlite3.Row], col: str, n: int = 3) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        v = str(r[col] or "").strip()
        if v:
            counts[v] = counts.get(v, 0) + 1
    return ", ".join(f"{k} ({v})" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n])


def _span(rows: list[sqlite3.Row]) -> str:
    ym = sorted((int(r["FIR_YEAR"]), int(r["FIR_MONTH"] or 1)) for r in rows if str(r["FIR_YEAR"] or "").isdigit())
    if not ym:
        return "dates not recorded"
    a, b = ym[0], ym[-1]
    return f"{a[0]}-{a[1]:02d}" if a == b else f"{a[0]}-{a[1]:02d} to {b[0]}-{b[1]:02d}"


def _network_from_firs(t: Target, rows: list[sqlite3.Row]) -> dict:
    """Other accused ids whose FIRs carry a vehicle, UPI or IP that this id's FIRs carry."""
    keys = {(c, str(r[c]).strip()) for r in rows for c, _ in _HARD_KEYS if str(r[c] or "").strip()}
    labels = dict(_HARD_KEYS)
    shared: dict[str, dict] = {}
    if keys:
        con = _brain_con()
        try:
            for col, val in sorted(keys):
                for (other, n) in con.execute(
                        f"SELECT Accused_ID, COUNT(*) FROM FIRs WHERE {col} = ? AND COALESCE(Accused_ID, '') "
                        "NOT IN ('', ?) GROUP BY Accused_ID", (val, t.accused)):
                    d = shared.setdefault(other, {"firs": 0, "keys": []})
                    d["firs"] += n
                    d["keys"].append(f"{labels[col]} {val}")
        finally:
            con.close()
    note = f"{t.accused} {_NOT_PROFILED}, so there are no recorded associate relationships to add."
    if not shared:
        why = "Its FIRs carry no vehicle, UPI or IP to link on." if not keys else \
              "No other accused id is on a FIR carrying the same vehicle, UPI or IP."
        return _empty(f"No other accused id is linked to {t.accused} by a shared key. {why}",
                      limits=[note, "No link on record is not the same as no connection."],
                      nxt=[f"run profile {t.accused}", f"run linkage {t.accused}"])
    ranked = sorted(shared.items(), key=lambda kv: (-kv[1]["firs"], kv[0]))
    return _ok("K", f"{_plural(len(shared), 'other accused id')} "
                    f"{'shares' if len(shared) == 1 else 'share'} a vehicle, UPI or IP with {t.accused}.",
               context=f"Read from the {_plural(len(rows), 'FIR')} that name {t.accused}.",
               evidence=[f"{o} · shares {', '.join(sorted(set(d['keys']))[:2])} · {_plural(d['firs'], 'FIR')}"
                         for o, d in ranked[:8]],
               limits=[note, "A shared key links cases; it does not by itself show an association."],
               nxt=[f"run linkage {t.accused}", f"run profile {t.accused}"])


def _profile_from_firs(t: Target, rows: list[sqlite3.Row]) -> dict:
    districts = sorted({str(r["District_Name"] or "").strip() for r in rows} - {""})
    return _ok("D", f"{t.accused} is named on {_plural(len(rows), 'FIR')} in "
                    f"{_plural(len(districts), 'district')}, {_span(rows)}.",
               evidence=[e for e in (f"Crime groups: {_top(rows, 'CrimeGroup_Name')}",
                                     f"Districts: {_top(rows, 'District_Name')}",
                                     f"Stations: {_top(rows, 'UnitName')}") if not e.endswith(": ")],
               limits=[f"No priority score: the scoring model reads the suspect registry, and {t.accused} "
                       "is not in it.", "A count of FIRs naming an accused is not a finding about the person."],
               nxt=[f"run network {t.accused}", f"run linkage {t.accused}"])


def _research_from_firs(t: Target, rows: list[sqlite3.Row]) -> dict:
    districts = sorted({str(r["District_Name"] or "").strip() for r in rows} - {""})
    keyed = sum(1 for r in rows if any(str(r[c] or "").strip() for c, _ in _HARD_KEYS))
    ev = [f"[K] Named as accused on {_plural(len(rows), 'FIR')} ({_span(rows)}).",
          f"[K] Crime groups on those FIRs: {_top(rows, 'CrimeGroup_Name')}.",
          f"[D] {_plural(len(districts), 'district')}: {', '.join(districts[:5])}"
          + (f" and {len(districts) - 5} more." if len(districts) > 5 else "."),
          f"[D] {keyed} of {len(rows)} FIRs carry a vehicle, UPI or IP to link on.",
          "[U] Name, age, address and known associates: no registry entry exists for this id."]
    return _ok("D", f"Dossier on {t.accused}: 2 known, 2 derived, 0 inferred, 1 unknown.",
               evidence=ev,
               limits=[f"{t.accused} {_NOT_PROFILED}. No hypothesis is proposed about an id with no profile."],
               nxt=[f"run network {t.accused}", "Collect: a registry entry for this accused id"])


def _recall_from_firs(t: Target, rows: list[sqlite3.Row]) -> dict:
    """Similar FIRs from the corpus, asked for with the newest FIR's own crime head and place."""
    from app.second_brain.retrieval import corpus_recall
    r = rows[0]
    query = " ".join(str(r[c] or "").strip() for c in ("CrimeHead_Name", "Place_of_Offence", "UnitName")).strip()
    hits = corpus_recall(query, k=5) if query else []
    if not hits:
        return _empty(f"No comparable record is recalled for the FIRs naming {t.accused}.",
                      nxt=[f"run linkage {t.accused}"])
    return _ok("D", f"{_plural(len(hits), 'similar FIR')} recalled for {t.accused}'s most recent case.",
               context=f"Searched on: {query}.",
               evidence=[f"FIR {h['meta'].get('fir_no')} · {h['meta'].get('district')} · "
                         f"{h['meta'].get('date')} · similarity {h['score']:.2f}" for h in hits],
               limits=["A similar FIR is a lead to check, not a finding, and not a link to this accused.",
                       f"{t.accused} {_NOT_PROFILED}, so cross-case links between suspects are not searched."],
               nxt=[f"run linkage {t.accused}"])


def _plural(n: int, word: str) -> str:
    if word == "person":
        return f"{n:,} {'person' if n == 1 else 'people'}"
    return f"{n:,} {word}" + ("" if n == 1 else "s")


# ── the agents ───────────────────────────────────────────────────────────────────

def _network(t: Target) -> dict:
    if (rows := _on_firs_only(t)):
        return _network_from_firs(t, rows)
    if (r := _need_suspect(t, "the network agent")):
        return r
    from app.agents.network_agent import build_network
    net = build_network(t.accused)
    nodes, edges, st = net.get("nodes") or [], net.get("edges") or [], net.get("stats") or {}
    seed = next((n for n in nodes if n.get("id") == t.accused), None)
    who = f"{seed.get('label')} [{t.accused}]" if seed and seed.get("label") else t.accused
    if len(nodes) <= 1 or not edges:
        return _empty(f"No associate links are recorded for {who}.",
                      limits=["An empty network means no link is on record, not that none exists."],
                      nxt=[f"run profile {t.accused}", f"run research {t.accused}"])
    names = {n["id"]: n.get("label") or n["id"] for n in nodes}
    mine = sorted((e for e in edges if t.accused in (e.get("a"), e.get("b"))),
                  key=lambda e: -(e.get("strength") or 0))
    ev = []
    for e in mine:
        other = e["b"] if e["a"] == t.accused else e["a"]
        ev.append(f"{names.get(other, other)} [{other}] · {str(e.get('rel_type') or 'link').replace('_', ' ')}"
                  f" · strength {e.get('strength')}" + (" · cross-case" if e.get("cross_case") else ""))
    limits = []
    if st.get("predicted_link_count"):
        limits.append(f"{_plural(st['predicted_link_count'], 'predicted link')} in the graph are "
                      f"inferences from similarity, not recorded relationships.")
    ctx = f"{_plural(st.get('inner_circle_count') or 0, 'person')} in the inner circle (k-core)."
    if net.get("broker_alert"):
        ctx += f" {net['broker_alert']}"
    return _ok("D", f"{who} is in a network of {_plural(len(nodes), 'person')} joined by "
                    f"{_plural(len(edges), 'recorded link')}.",
               context=ctx, evidence=ev, limits=limits,
               nxt=[f"run research {t.accused}", f"run advocate {t.accused}"])


def _profile(t: Target) -> dict:
    if (rows := _on_firs_only(t)):
        return _profile_from_firs(t, rows)
    if (r := _need_suspect(t, "the profiler")):
        return r
    from app.agents import profile_agent
    p = profile_agent.compute_profile(t.accused)
    if not p:
        return _refuse(f"I can't profile {t.accused}: the registry returned no record.")
    attr = sorted((p.get("risk_attributions") or {}).items(), key=lambda kv: -kv[1])
    raw = p.get("raw_factors") or {}
    basis = {"frequency": f"{raw.get('frequency')} linked cases", "severity": f"severity {raw.get('severity')}",
             "centrality": f"centrality {raw.get('centrality')}",
             "recency": f"{raw.get('recency_days')} days since the last case"}
    ev = [f"{k.capitalize()} +{v:.1f} points ({basis.get(k, '')})" for k, v in attr]
    assoc = p.get("associates") or []
    if assoc:
        ev.append(f"{_plural(len(assoc), 'associate')} on record, e.g. "
                  + ", ".join(f"{a.get('name')} [{a.get('id')}]" for a in assoc[:3]))
    limits = ["The score orders cases for attention. It is not a forecast of what this person will do."]
    limits += [str(w) for w in (p.get("bias_warnings") or [])]
    return _ok("D", f"{p.get('full_name')} [{t.accused}] scores {p.get('risk_score'):.0f} of 100 "
                    f"on the priority model.",
               context=str(p.get("mo_summary") or ""), evidence=ev, limits=limits,
               nxt=[f"run network {t.accused}", f"run recall {t.accused}"])


def _dossier(sid: str) -> dict:
    from app.agents.research_agent import run_research
    return run_research(sid)


def _tally_line(review: dict) -> str:
    ta = review.get("tally") or {}
    return (f"{ta.get('COLLAPSES', 0)} collapse, {ta.get('WEAKENED', 0)} weakened, "
            f"{ta.get('SURVIVES', 0)} survive")


def _research(t: Target) -> dict:
    if (rows := _on_firs_only(t)):
        return _research_from_firs(t, rows)
    if (r := _need_suspect(t, "the research agent")):
        return r
    from app.agents.advocate_agent import challenge_dossier
    d = _dossier(t.accused)
    k, dv = d.get("known_facts") or [], d.get("derived_facts") or []
    hyp, gaps = d.get("inferred_hypotheses") or [], d.get("unknown_gaps") or []
    if not k:
        return _empty(f"There is no verified record to build a dossier on for {t.accused}.")
    ev = [f"[K] {f.get('claim')}" for f in k[:2]] + [f"[D] {f.get('claim')}" for f in dv[:2]]
    ev += [f"[I] {h.get('claim')}" for h in sorted(hyp, key=lambda h: -(h.get("score") or 0))[:2]]
    ev += [f"[U] {g.get('what_is_missing')}" for g in gaps[:2]]
    limits = []
    if hyp:
        # A dossier's inferences never leave this agent without the base-rate check.
        review = challenge_dossier(d)
        limits.append(f"Adversary review of the inferences: {_tally_line(review)}.")
    return _ok("D", f"Dossier on {t.accused}: {len(k)} known, {len(dv)} derived, {len(hyp)} "
                    f"inferred, {len(gaps)} unknown.",
               evidence=ev, limits=limits,
               nxt=[f"run advocate {t.accused}"] + ([f"Collect: {gaps[0].get('collect_action')}"] if gaps else []))


def _advocate(t: Target) -> dict:
    if _on_firs_only(t):
        # Research proposes no hypothesis about an unprofiled id, so there is nothing to price.
        return _empty(f"There is no hypothesis about {t.accused} to challenge: it {_NOT_PROFILED}, "
                      f"and none is proposed about an id with no profile.",
                      nxt=[f"run research {t.accused}", f"run linkage {t.accused}"])
    if (r := _need_suspect(t, "the adversary")):
        return r
    from app.agents.advocate_agent import challenge_dossier
    d = _dossier(t.accused)
    if not (d.get("inferred_hypotheses") or []):
        return _empty(f"There is no hypothesis about {t.accused} to challenge.",
                      nxt=[f"run research {t.accused}"])
    rv = challenge_dossier(d)
    ch = rv.get("challenges") or []
    ev = []
    for c in ch:
        post = (c.get("combined") or {}).get("posterior_probability")
        ev.append(f"{c.get('verdict') or (c.get('combined') or {}).get('strength') or '-'} · "
                  f"{c.get('original_claim')}"
                  + (f" · posterior {post:.2f}" if isinstance(post, (int, float)) else ""))
    return _ok("D", f"{len(ch)} {'hypothesis' if len(ch) == 1 else 'hypotheses'} about "
                    f"{t.accused} challenged: {_tally_line(rv)}.",
               context=f"Priced against {rv.get('population'):,} suspects in the registry; no LLM."
               if isinstance(rv.get("population"), int) else "Frequency-based likelihood ratios; no LLM.",
               evidence=ev, limits=[str(s) for s in (rv.get("systemic_defects") or [])],
               nxt=[f"run research {t.accused}"])


def _brain(t: Target) -> dict:
    if (rows := _on_firs_only(t)):
        return _recall_from_firs(t, rows)
    if (r := _need_suspect(t, "recall")):
        return r
    from app.second_brain.retrieval import find_cross_case_links
    links = (find_cross_case_links(t.accused) or {}).get("links") or []
    if not links:
        return _empty(f"No comparable record is recalled for {t.accused}.",
                      nxt=[f"run network {t.accused}"])
    ev = [f"{l.get('full_name')} [{l.get('suspect_id')}] · {str(l.get('overlap_type') or '').replace('_', ' ')}"
          f" · {l.get('shared_contact_count') or 0} shared contacts · FIR {l.get('anchor_fir')}"
          f" ({l.get('anchor_zone')}) · about {l.get('months_ago')} months ago" for l in links]
    return _ok("D", f"{_plural(len(links), 'cross-case link')} recalled for {t.accused}.",
               evidence=ev, limits=["A recalled link is a lead to check, not a finding."],
               nxt=[f"run advocate {t.accused}", f"run network {t.accused}"])


def _linkage(t: Target) -> dict:
    from app.agents import linkage_agent
    from app.services import evidence_ledger
    if t.fir_ref:
        # A typed EV- reference is a row of the evidence CSV, and only that.
        res = evidence_ledger.linkage(t.fir_ref)
        if res is None:
            return _refuse(f"{t.fir_ref} is not a reference in the evidence ledger.")
        cands = res["candidates"]
        if not cands:
            return _empty(f"No other FIR shares an accused, vehicle, UPI or IP with {t.fir_ref}.",
                          limits=["Only exact hard keys are matched."])
        return _ok("K", f"{_plural(len(cands), 'other FIR')} {'shares' if len(cands) == 1 else 'share'} "
                        f"a hard key with {t.fir_ref}.",
                   evidence=[f"{c.get('linked_fir_id')} · {c.get('crime_type')} · {c.get('district')} · "
                             f"{c.get('date')} · {'; '.join(c.get('reason_chips') or [])}" for c in cands])

    # A record on the Brain graph is matched by the keys it carries - it has no usable id.
    res = linkage_agent.brain_linkage({"Accused_ID": t.accused, "Vehicle_Reg_No": t.vehicle,
                                       "UPI_ID": t.upi, "IP_Address": t.ip})
    if not res["keys"]:
        return _empty("This record carries no accused, vehicle, UPI or IP, so there is nothing "
                      "to link it on.",
                      limits=["An unlinked FIR is unlinked on record, not shown to be unconnected."])
    parts = [f"{name} {k['value']} on {_plural(k['firs'], 'FIR')}" for name, k in res["by_key"].items()]
    if res["total"] <= 1:
        return _empty(f"No other FIR in the Brain dataset carries {' or '.join(p.split(' on ')[0] for p in parts)}.",
                      limits=["Only exact hard keys are matched."])
    ev = [f"{r['crime_type']} · {r['station']}, {r['district']} · {r['when']} · shares {', '.join(r['shares'])}"
          for r in res["rows"]]
    bottom = (f"{_plural(res['total'], 'FIR')} in the Brain dataset carry {parts[0].split(' on ')[0]}."
              if len(parts) == 1 else
              f"{_plural(res['total'], 'FIR')} in the Brain dataset carry this record's keys: {'; '.join(parts)}.")
    return _ok("K", bottom,
               context=("Showing the first " + str(len(ev)) + ". " if res["total"] > len(ev) else "")
                       + "The count includes the record itself. A shared key links cases; it does "
                         "not by itself show one operation.",
               evidence=ev,
               nxt=([f"run network {t.accused}"] if t.accused and _in_registry(t.accused) else []))


def _forecast_call(fn: Callable, **kw) -> dict | Any:
    from app.forecast import service as S
    con = _ro()
    try:
        return fn(S, con, **kw)
    except S.Refusal as r:
        return _refuse(r.message + (f" Try: {', '.join(r.options[:4])}." if r.options else ""))
    except S.NotReady as n:
        return _refuse(str(n))
    finally:
        con.close()


def _forecast(t: Target) -> dict:
    if not t.station:
        return _refuse("I can't forecast for a person. Drop this agent on a FIR to forecast its "
                       "police station, or type a station name.", nxt=["run geo"])
    u = _forecast_call(lambda S, con: S.unit_detail(con, t.station))
    if "status" in u:
        return u
    ev = [f"{d.get('effect')} · {d.get('text')}" for d in
          ((u.get("forecast") or {}).get("7") or (u.get("forecast") or {}).get(7) or {}).get("drivers") or []]
    tr = u.get("track_record") or {}
    if tr.get("text"):
        ev.append(f"Track record: {tr['text']}")
    limits = list(u.get("limits") or [])
    basis = (u.get("as_of") or {}).get("basis")
    if basis:
        limits.insert(0, basis[0].upper() + basis[1:])
    return _ok("I", str(u.get("bottom_line") or f"No forecast is on file for {t.station}."),
               context=f"{u.get('name') or t.station}, {u.get('district')} · {u.get('category_label')}"
                       f" · as of {(u.get('as_of') or {}).get('as_of')}",
               evidence=ev, limits=limits, nxt=[f"run geo {u.get('district') or ''}".strip()])


def _geo(t: Target) -> dict:
    place = t.district or t.station
    if not place:
        return _refuse("I can't map a person. Drop this agent on a FIR to scan its district, or "
                       "type a district name.", nxt=["run network"])

    def work(S, con):
        # A typed word arrives as `station`: it may name a district ("run geo Mysuru City").
        district = (t.district or S.resolve_district(con, t.station)
                    or S.unit_detail(con, t.station).get("district"))
        return S.hotspots(con, district=district, unit_type="beat", limit=5)

    h = _forecast_call(work)
    if "status" in h:
        return h
    ev = [f"{i.get('rank')}. {i.get('name')} · {i.get('station')} · {i.get('summary')}"
          for i in h.get("items") or []]
    return _ok("I", str(h.get("bottom_line") or f"No beats are forecast for {h.get('scope')}."),
               context=f"{h.get('scope')} · {h.get('category_label')} · next {h.get('horizon_days')} days"
                       f" · {h.get('units_forecast')} beats forecast",
               evidence=ev, limits=list(h.get("limits") or []),
               nxt=[f"run forecast {(h.get('items') or [{}])[0].get('station') or ''}".strip()])


def _pattern(t: Target) -> dict:
    if not t.crime_group:
        return _refuse("I can't look for a pattern without a crime type. Drop this agent on a FIR "
                       "so it can take the FIR's crime group.")
    from app.services.patterns import find_clusters
    from app.services.zcql_local import scan_rows
    rows = scan_rows(t.crime_group, None)
    clusters = find_clusters(rows)
    scope = ""
    if t.district:
        clusters = [c for c in clusters if t.district in (c.get("zones") or [])]
        scope = f" in {t.district}"
    what = t.crime_group.title()
    if not clusters:
        return _empty(f"No space-time cluster of {what} is on record{scope}.",
                      limits=[f"Scanned {len(rows):,} FIRs of this crime group."])
    clusters.sort(key=lambda c: (not c.get("is_active"), -(c.get("size") or 0)))
    active = sum(1 for c in clusters if c.get("is_active"))
    return _ok("D", f"{_plural(len(clusters), 'space-time cluster')} of {what} on record{scope}; "
                    f"{active} still active.",
               context=f"Density clustering over {len(rows):,} FIRs of this crime group.",
               evidence=[str(c.get("explanation")) for c in clusters],
               limits=["A cluster is cases close in place and time. It does not show a common offender."],
               nxt=["run geo", "run linkage"])


# ── the cards: identity and method per agent ─────────────────────────────────────

@dataclass(frozen=True)
class Card:
    manifest: str             # the agent's id in AGENTS.md
    name: str
    needs: str                # "suspect" | "FIR" | "station" | "district" | "crime type"
    purpose: str
    method: tuple[str, ...]   # how it works a new problem - the steps its handler takes
    refuses: str
    run: Callable[[Target], dict]


AGENTS: dict[str, Card] = {
    "network": Card("network", "Network", "suspect", "Who this person is connected to, and how.",
                    ("Find the suspect in the registry", "Expand recorded links two hops out",
                     "Rank everyone by PageRank and k-core", "Keep recorded and predicted links apart"),
                    "Never invents a seed: no accused on the record, no network.", _network),
    "profile": Card("profile", "Profile", "suspect", "How much attention this person's record warrants, and why.",
                    ("Read the suspect's cases", "Score frequency, severity, centrality and recency",
                     "Attribute the score to each factor exactly", "Screen the wording for bias"),
                    "Never predicts what an individual will do.", _profile),
    "research": Card("research", "Research", "suspect", "Everything on record about a subject, sorted by how sure it is.",
                     ("Collect what is Known", "Compute what is Derived", "Propose scored hypotheses",
                      "List what is Unknown and how to collect it", "Send every hypothesis to the adversary"),
                     "Never researches an unnamed subject.", _research),
    "advocate": Card("advocate_agent", "Adversary", "suspect", "Argues against Antar's own hypotheses.",
                     ("Take each hypothesis about the subject", "Price every signal at its base rate",
                      "Correct for how many pairs were scanned", "Rule: survives, weakened or collapses"),
                     "Uses no LLM, and never silently approves a hypothesis.", _advocate),
    # Named Recall here, not Brain: on the Brain screen "Brain" already means the whole
    # graph. The agent it runs is still the manifest's `brain` (semantic recall).
    "recall": Card("brain", "Recall", "suspect", "Has something like this been seen before, in another case?",
                  ("Search the curated memory and the FIR corpus", "Rerank by corroboration",
                   "Return each hit as a lead with its anchor FIR"),
                  "Reports 'no comparable record' rather than staying silent.", _brain),
    "linkage": Card("linkage", "Linkage", "FIR", "Which other FIRs share hard evidence with this one.",
                    ("Take the FIR's accused, vehicle, UPI and IP", "Find every FIR sharing one",
                     "Score by key type and name the shared key"),
                    "Never asserts a match without a shared key.", _linkage),
    "forecast": Card("forecast", "Forecast", "station", "How many FIRs to expect at this station next week.",
                     ("Resolve the station", "Read its calibrated range for the next 7 days",
                      "List the reasons that move it", "State what share of the history is real record"),
                     "Forecasts places, never people, and never a calendar date.", _forecast),
    "geo": Card("geo", "Geo", "district", "Where in this district to look next.",
                ("Resolve the district", "Rank its beats by expected FIRs", "Give each beat its likely range"),
                "Maps places, never people.", _geo),
    "pattern": Card("pattern", "Pattern", "crime type", "Whether this kind of crime is clustering in place and time.",
                    ("Take the FIR's crime group", "Cluster its FIRs by distance and date",
                     "Separate active clusters from historic ones"),
                    "A cluster is never presented as a common offender.", _pattern),
}


def identity_pack() -> dict:
    """Antar's identity and each console agent's card - what the Brain screen displays.

    Roles and timeouts are read from the manifest, so a card cannot describe an agent
    AGENTS.md does not declare (tests/test_brain_console.py asserts each one resolves).
    """
    from app.agents import manifest
    declared = manifest.load().agents
    agents = []
    for key, c in AGENTS.items():
        m = declared.get(c.manifest)
        agents.append({"id": key, "name": c.name, "role": m.role if m else "", "needs": c.needs,
                       "purpose": c.purpose, "method": list(c.method), "refuses": c.refuses,
                       "guardrails": list(m.guardrails) if m else []})
    return {
        "name": identity.NAME, "meaning": "ಅಂತರ್ - within",
        "version": identity.VERSION, "since": identity.SINCE,
        "role": identity.ROLE[0].upper() + identity.ROLE[1:] + ".",
        "laws": [{"law": n, "rule": r} for n, r in identity.LAWS],
        "thinking": [{"step": n, "how": h} for n, h in identity.THINKING],
        "usps": [{"claim": c, "how": h} for c, h in identity.USPS],
        "classes": {k: {"name": v["en"], "desc": v["desc"]} for k, v in identity.CLASSES.items()},
        "agents": agents,
        "commands": COMMANDS,
    }


def evolution() -> dict:
    """How Antar has changed with use - each line counted from the store that records it.

    Not a claim that Antar is better than it was: a count is a count. A line whose store
    cannot be read says so; it never shows a zero that would read as "nothing happened".
    """
    rows: list[dict] = []

    def line(what: str, fn: Callable[[], tuple[str, str]]) -> None:
        try:
            value, how = fn()
        except Exception as e:                       # one unreadable store must not hide the rest
            value, how = "not available", f"this store could not be read ({type(e).__name__})"
        rows.append({"what": what, "value": value, "how": how})

    def ratings():
        from app.api.feedback import _tally
        t = list(_tally().values())
        up, down = sum(q["up"] for q in t), sum(q["down"] for q in t)
        usable = sum(1 for q in t if q["up"] > q["down"])
        return (f"{_plural(up + down, 'rating')} from officers: {up} useful, {down} not",
                f"{_plural(usable, 'question')} now {'has' if usable == 1 else 'have'} a rated answer that "
                "shapes the next similar one; a thumbs-down removes it")

    def forecast():
        from app.forecast import service as S
        con = _ro()
        try:
            sc = S.scorecard(con, unit_type="beat", category=None)
        finally:
            con.close()
        weeks = sc.get("weeks") or []
        beat = sum(1 for w in weeks if w.get("beat_last4"))
        return (f"{_plural(len(weeks), 'forecast week')} graded, {beat} ahead of the last-4-weeks baseline",
                f"each week forecast from the data before it, real record {sc['window']['from']} to {sc['window']['to']}")

    def adversary():
        con = _ro()
        try:
            n = dict(con.execute("SELECT type, COUNT(*) FROM audit_log WHERE type IN "
                                 "('hypothesis_confirmed', 'hypothesis_rejected') GROUP BY type"))
        finally:
            con.close()
        confirmed, rejected = n.get("hypothesis_confirmed", 0), n.get("hypothesis_rejected", 0)
        return (f"{_plural(confirmed + rejected, 'hypothesis decision')} recorded: {confirmed} confirmed, {rejected} rejected",
                "each one went past the base-rate adversary first; its verdict and the officer's reason are on the audit chain")

    def ledger():
        from app.services import audit_store
        r = audit_store.verify_chain_report()
        state = "every entry verified" if r.get("ok") and not r.get("legacy_unverifiable") else (
            f"{r.get('verified', 0):,} verified" + (f", broken at entry {r['broken_at_index']}" if r.get("broken_at_index") is not None else ""))
        return (f"{r.get('total_entries', 0):,} audit entries, {state}", "hash-chained; a changed entry breaks the chain from that point on")

    def memory():
        from app.second_brain import vec_store
        by = vec_store.stats()["by_kind"]
        firs, curated = by.get("fir", 0), sum(n for k, n in by.items() if k != "fir")
        return (f"{firs:,} FIRs and {_plural(curated, 'curated note')} in recall",
                "a similar FIR is returned as a lead (Derived), never as a finding")

    line("Identity", lambda: (f"Constitution {identity.VERSION}, in force since {identity.SINCE}",
                              f"{len(identity.LAWS)} laws and {len(identity.THINKING)} working steps, the same on every answer"))
    line("Learned from officers", ratings)
    line("Forecast, graded", forecast)
    line("Challenged before confirmed", adversary)
    line("Accountable", ledger)
    line("Memory", memory)
    return {"name": identity.NAME, "version": identity.VERSION, "since": identity.SINCE, "record": rows}


def starting_points() -> dict:
    """Records an agent can be pointed at when an answer names none of its own.

    A statewide answer ("IPC against special laws in 2023") has no accused, station or
    district in it, so every agent in the workspace sat disabled. These are offered instead:
    the district, station and crime group with the most FIRs dated today, and the accused id
    named on the most FIRs in the Brain dataset. Each says why it was picked - a count, not a
    judgment that it is the right place to look.
    """
    from datetime import date
    d0 = date.today().isoformat()
    out: list[dict] = []
    con = _ro()
    try:
        for kind, col, word in (("district", "District_Name", "district"), ("station", "UnitName", "station"),
                                ("crime_group", "CrimeGroup_Name", "crime group")):
            try:
                row = con.execute(f"SELECT {col}, COUNT(*) FROM FIRs WHERE date = ? AND COALESCE({col}, '') <> '' "
                                  "GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1", (d0,)).fetchone()
            except sqlite3.OperationalError:
                row = None
            if row:
                out.append({"kind": kind, "value": row[0],
                            "why": f"the {word} with the most FIRs dated today ({row[1]:,})"})
    finally:
        con.close()
    try:
        bc = _brain_con()
        try:
            row = bc.execute("SELECT Accused_ID, COUNT(*) FROM FIRs WHERE COALESCE(Accused_ID, '') <> '' "
                             "GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1").fetchone()
        finally:
            bc.close()
        if row:
            out.append({"kind": "accused", "value": row[0],
                        "why": f"the accused id named on the most FIRs in the Brain dataset ({row[1]:,})"})
    except sqlite3.OperationalError:
        pass
    return {"date": d0, "targets": out}


_learn_cache: tuple[float, dict] | None = None


def learnings() -> dict:
    """What the records show today that an officer would want said - each line counted.

    These are the lines the agents pass each other on the Brain screen. "Learning" here
    means a count read from the registry for today's date, set against yesterday or the
    week before it; nothing is trained and nothing is inferred. A line whose source cannot
    be read is left out rather than shown as a zero, and each carries the rows behind it so
    the terminal can show the working when an officer clicks it.

    `from` and `to` name console agents: the one whose kind of work found the line, and the
    one that would act on it.
    """
    global _learn_cache
    if _learn_cache and time.time() - _learn_cache[0] < 60:
        return _learn_cache[1]
    from datetime import date, timedelta
    today = date.today()
    d0, d1 = today.isoformat(), (today - timedelta(days=1)).isoformat()
    week_from = (today - timedelta(days=7)).isoformat()
    out: list[dict] = []

    def add(key: str, frm: str, to: str, cls: str, text: str, title: str, rows: list, source: str) -> None:
        out.append({"id": f"{d0}:{key}", "from": frm, "to": to, "evidence_class": cls, "text": text,
                    "title": title, "rows": [[str(a), str(b)] for a, b in rows], "source": source})

    def registry(con: sqlite3.Connection) -> None:
        by_day = dict(con.execute("SELECT date, COUNT(*) FROM FIRs WHERE date BETWEEN ? AND ? GROUP BY date",
                                  (week_from, d0)))
        n0, n1 = by_day.get(d0, 0), by_day.get(d1, 0)
        prior = [by_day.get((today - timedelta(days=k)).isoformat(), 0) for k in range(1, 8)]
        avg = sum(prior) / 7
        add("volume", "pattern", "forecast", "K",
            f"{_plural(n0, 'FIR')} {'is' if n0 == 1 else 'are'} dated today. Yesterday had {n1:,}; "
            f"the seven days before today averaged {avg:.0f} a day.",
            f"FIRs dated {d0}",
            [(f"Today ({d0})", f"{n0:,}"), (f"Yesterday ({d1})", f"{n1:,}"), ("Seven-day average", f"{avg:.1f} a day")]
            + [((today - timedelta(days=k)).isoformat(), f"{by_day.get((today - timedelta(days=k)).isoformat(), 0):,}")
               for k in range(2, 8)],
            "registry, by FIR date")
        if not n0:
            return                                  # nothing dated today: no shares or movers to state

        dist = con.execute("SELECT District_Name, COUNT(*) FROM FIRs WHERE date = ? AND COALESCE(District_Name, '') <> '' "
                           "GROUP BY District_Name ORDER BY 2 DESC, 1 LIMIT 5", (d0,)).fetchall()
        if dist:
            top, n = dist[0]
            add("district", "geo", "forecast", "D",
                f"{top} has {n:,} of today's {_plural(n0, 'FIR')} ({round(100 * n / n0)}%).",
                f"Where today's FIRs were registered ({d0})",
                [(d, f"{c:,} ({round(100 * c / n0)}%)") for d, c in dist], "registry, FIRs dated today by district")

        today_g = dict(con.execute("SELECT CrimeGroup_Name, COUNT(*) FROM FIRs WHERE date = ? GROUP BY 1", (d0,)))
        week_g = dict(con.execute("SELECT CrimeGroup_Name, COUNT(*) FROM FIRs WHERE date >= ? AND date < ? GROUP BY 1",
                                  (week_from, d0)))
        # A mover is a group with enough FIRs today to be worth saying (5), set against its
        # own daily average over the seven days before. Small counts are left out: 1 to 3 is
        # +200% and two cases.
        movers = sorted(((g, c, week_g.get(g, 0) / 7) for g, c in today_g.items() if g and c >= 5),
                        key=lambda m: (-(m[1] - m[2]), m[0]))
        if movers and movers[0][1] > movers[0][2]:
            g, c, a = movers[0]
            add("mover", "pattern", "linkage", "D",
                f"{str(g).title()}: {c:,} today against a seven-day average of {a:.1f} a day.",
                f"Crime groups above their own week ({d0})",
                [(str(m[0]).title(), f"{m[1]:,} today · {m[2]:.1f} a day last week") for m in movers[:5] if m[1] > m[2]],
                "registry, today against the seven days before")

    def alerts() -> None:
        from app.services import alerts_store
        top = alerts_store.list_recent(3)
        if not top:
            return
        a = top[0]
        z = a.get("z_score")
        add("alert", "forecast", "geo", "D",
            f"{a.get('zone')}: {str(a.get('crime_type') or '').replace('_', ' ').lower()} is above its usual level"
            f" ({a.get('observed')} recorded" + (f", {z:.1f} deviations above" if isinstance(z, (int, float)) else "") + ").",
            "Open anomaly alerts",
            [(f"{x.get('zone')} · {str(x.get('crime_type') or '').replace('_', ' ').lower()}",
              f"{x.get('observed')} recorded" + (f" · z {x.get('z_score'):.1f}" if isinstance(x.get("z_score"), (int, float)) else ""))
             for x in top], "anomaly scan")

    def ratings() -> None:
        from app.api.feedback import _read, _tally
        import datetime as _dt
        start = _dt.datetime.combine(today, _dt.time.min).timestamp()
        mine = [e for e in _read() if float(e.get("ts") or 0) >= start and e.get("rating") in ("up", "down")]
        up = sum(1 for e in mine if e["rating"] == "up")
        usable = sum(1 for q in _tally().values() if q["up"] > q["down"])
        text = (f"Officers rated {_plural(len(mine), 'answer')} today: {up} useful, {len(mine) - up} not."
                if mine else "No answer has been rated today.")
        add("ratings", "recall", "research", "K",
            f"{text} {_plural(usable, 'rated answer')} now {'shapes' if usable == 1 else 'shape'} similar answers.",
            "What officers rated today",
            [("Rated today", f"{len(mine)}"), ("Useful", f"{up}"), ("Not useful", f"{len(mine) - up}"),
             ("Rated answers in use", f"{usable}")], "answer ratings")

    con = _ro()
    try:
        for fn in (lambda: registry(con), alerts, ratings):
            try:
                fn()
            except Exception:                        # a source that cannot be read is left out
                continue
    finally:
        con.close()
    res = {"date": d0, "learnings": out}
    _learn_cache = (time.time(), res)
    return res


# The whole command set. The terminal accepts nothing else; an unknown word is answered
# with the nearest of these, never passed to a model.
COMMANDS = [
    {"cmd": "help [command]", "does": "List these commands, or show examples for one."},
    {"cmd": "agents", "does": "List the agents and what each one needs."},
    {"cmd": "about <agent>", "does": "How that agent works a problem, and what it refuses."},
    {"cmd": "select <id>", "does": "Pick a record by accused id, e.g. select S0041."},
    {"cmd": "run <agent> [target]", "does": "Run an agent on the target, or on the selected record."},
    {"cmd": "fastrun", "does": "Fast Run: scan the records in the current view for findings."},
    {"cmd": "assemble", "does": "Call the agents into a line."},
    {"cmd": "roam", "does": "Release the agents to walk the brain again."},
    {"cmd": "memory [agent]", "does": "What the agents remember running this session."},
    {"cmd": "log", "does": "The messages agents sent each other."},
    {"cmd": "auto on|off", "does": "Whether an agent hands its record to the next agent, which then answers."},
    {"cmd": "notify on|off", "does": "Also raise results through the system when this tab is in the background."},
    {"cmd": "forget", "does": "Clear the agents' memory and message log."},
    {"cmd": "why", "does": "The steps the last agent took."},
    {"cmd": "identity", "does": "Who Antar is, its laws and how it thinks."},
    {"cmd": "evolution", "does": "How Antar has changed with use: ratings, graded forecasts, challenged hypotheses."},
    {"cmd": "learnings", "does": "What the records show today: FIRs dated today, movers, alerts, ratings."},
    {"cmd": "think", "does": "Think: scan the records in the current view (the same as fastrun). /think also works."},
    {"cmd": "connect [id]", "does": "Connect: run Network then Linkage on an accused id, or on the selected record."},
    {"cmd": "anticipate [place]", "does": "Anticipate: Forecast for a station, Geo for a district. Places only, never a person."},
    {"cmd": "history", "does": "The commands typed this session."},
    {"cmd": "clear", "does": "Clear the terminal."},
]


def run(agent: str, target: Any) -> dict:
    """Run one console agent on one target. Never raises: a failure is a degraded result
    that says so, because a console that throws shows the officer nothing at all."""
    key = str(agent or "").strip().lower()
    card = AGENTS.get(key)
    if card is None:
        import difflib
        near = difflib.get_close_matches(key, list(AGENTS), n=1, cutoff=0.5)
        return {"agent": key, **_refuse(f"There is no agent called '{agent}'."
                                        + (f" Did you mean {near[0]}?" if near else ""),
                                        nxt=["agents"])}
    t = parse_target(target)
    ck = (key, t.key())
    hit = _cache.get(ck)
    if hit and time.monotonic() - hit[0] < _CACHE_TTL_S:
        return {**hit[1], "cached": True}
    t0 = time.perf_counter()
    try:
        body = card.run(t)
    except Exception as e:
        import structlog
        structlog.get_logger(__name__).warning("console_agent_failed", agent=key,
                                               error=f"{type(e).__name__}: {e}")
        body = {"status": "error", "evidence_class": None,
                "bottom_line": f"The {card.name.lower()} agent could not complete on {t.label or 'this record'}.",
                "context": "", "evidence": [], "limits": ["Nothing is shown rather than a partial result."],
                "next": []}
    for f in ("bottom_line", "context"):
        body[f] = identity.protect(str(body.get(f) or ""))
    body["evidence"] = [identity.protect(str(x)) for x in body.get("evidence") or []]
    out = {"agent": key, "name": card.name, "target": t.label, "method": list(card.method),
           "ms": int((time.perf_counter() - t0) * 1000), "cached": False, **body}
    if body["status"] in ("ok", "empty"):
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[ck] = (time.monotonic(), out)
    return out
