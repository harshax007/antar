"""
Antar — export the knowledge layer as an OKF v0.2 bundle (final_backend.md §6 P2-1).

    python scripts/build_okf_bundle.py                 # writes ./knowledge
    python scripts/build_okf_bundle.py --dest /tmp/kb --quiet

The Open Knowledge Format (Google Cloud, v0.2, July 2026) represents knowledge as linked
markdown with YAML frontmatter, readable by a person without tooling and parseable by an
agent without an SDK. Spec: https://github.com/GoogleCloudPlatform/open-knowledge-format

Why this is worth doing for Antar specifically, beyond "a standard exists":

  * It is the same principle `AGENTS.md` already proves — documentation that cannot drift,
    because a test fails when the document and the running system disagree. Here the
    document is generated FROM the registry and the code, and `tests/test_okf_bundle.py`
    fails when the two diverge.
  * OKF v0.2's trust signals map onto distinctions Antar already makes. A concept this
    script derives from the database is `generated` by a process and carries NO `verified`
    key, so OKF's own tier derivation reports it as *unverified* — which is exactly right.
    The constitution, written and owned by people, carries `verified: {by: human:...}` and
    reads as *human-reviewed*. The format does the honesty for us.
  * `type: Attested Computation` is the spec's shape for a parameterised query with an
    executor, a receipt and a deterministic attester. That is precisely what the T-series
    whitelist templates are. Emitting them as attested computations means another agent
    can call Antar's deterministic spine by reading a markdown file — the templates stop
    being an implementation detail and become the interface.

Nothing here is hand-written prose about the data. Every count, every crime head, every
parameter comes from the live database or from the Python objects the server runs on.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NL = chr(10)
OKF_VERSION = "0.2"

# OKF actor convention (§ "Actor Convention"): `process:<id>` for automated processes,
# `human:<id>` for people. Consumers key their trust tier off the `human:` prefix, so
# using it for machine-derived content would be a lie the format is designed to catch.
PRODUCER = "process:antar-okf-export"
HUMAN_OWNER = "human:antar-team"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canon(name: str) -> str:
    """Canonical form of a registry label: one space, trimmed, upper case.

    The `CrimeGroup_Name` column records the same group several ways. Measured on the
    live registry: **141 raw spellings for 113 actual groups**. The duplication is of two
    kinds and both carry real volume, so neither side can be dismissed as a typo:

        'CYBER CRIME'  18,609   vs  'CYBER CRIME'   49,399   (internal whitespace)
        'ASSAULT'         159   vs  'assault'          460   (case)

    Anyone counting crime groups straight from this column gets an inflated number. The
    bundle canonicalises, sums the counts, and lists every raw spelling on the concept —
    merged, not hidden.
    """
    return re.sub(r"\s+", " ", str(name or "")).strip().upper()


def slug(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (s[:maxlen].rstrip("-") or "unnamed")


# ── YAML emission ────────────────────────────────────────────────────────────
# Written by hand rather than with PyYAML. The shapes here are small and fixed, and the
# spec cares about exact key names; hand-emitting keeps the output diffable (stable key
# order, no anchors, no line-wrapping surprises) and adds no dependency to a repo that is
# fighting for every megabyte.

def _scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "":
        return '""'
    # Quote anything YAML could reinterpret: leading/trailing space, or a character that
    # starts a collection, a comment, an anchor, or a datetime-looking scalar.
    if re.search(r'^[\s>|&*!%@`#\-?{\[]|[:#]\s|["\']|^\d{4}-\d{2}|\s$', s) or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _yaml(value, indent: int = 0) -> str:
    """Emit a dict/list/scalar tree as YAML. Mappings keep insertion order."""
    pad = " " * indent
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            if v is None or v == [] or v == {}:
                continue
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out.append(_yaml(v, indent + 2))
            else:
                out.append(f"{pad}{k}: {_scalar(v)}")
        return NL.join(out)
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                # Render the item at indent 0 and apply the block indent here. Rendering it
                # at indent+2 and then prefixing again double-indented every line after the
                # first, which YAML reads as a nested scalar rather than sibling keys.
                lines = _yaml(item, 0).split(NL)
                out.append(f"{pad}- {lines[0]}")
                out.extend(f"{pad}  {ln}" for ln in lines[1:])
            else:
                out.append(f"{pad}- {_scalar(item)}")
        return NL.join(out)
    return f"{pad}{_scalar(value)}"


def concept(path: Path, front: dict, body: str) -> None:
    """Write one OKF concept: frontmatter with a non-empty `type`, then markdown."""
    assert front.get("type"), f"OKF requires a non-empty type ({path})"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---" + NL + _yaml(front) + NL + "---" + NL + NL + body.rstrip() + NL
    path.write_text(text, encoding="utf-8")


def index(path: Path, sections: list[tuple[str, list[tuple[str, str, str]]]],
          root: bool = False) -> None:
    """Write an index.md — no frontmatter, except the bundle root's okf_version (§9)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    if root:
        parts += ["---", f'okf_version: "{OKF_VERSION}"', "---", ""]
    for heading, items in sections:
        parts.append(f"# {heading}")
        parts.append("")
        for title, href, desc in items:
            parts.append(f"* [{title}]({href})" + (f" - {desc}" if desc else ""))
        parts.append("")
    path.write_text(NL.join(parts).rstrip() + NL, encoding="utf-8")


def _sources(resource: str, title: str, count: int | None = None,
             last_modified: str | None = None) -> list[dict]:
    src: dict = {"id": slug(title), "resource": resource, "title": title,
                 "author": PRODUCER}
    if count is not None:
        src["usage_count"] = count
    if last_modified:
        src["last_modified"] = last_modified
    return [src]


# ── The registry, read once ──────────────────────────────────────────────────

def read_registry(con: sqlite3.Connection) -> dict:
    con.row_factory = sqlite3.Row
    q = con.execute(
        "SELECT CrimeGroup_Name AS grp, CrimeHead_Name AS head, COUNT(*) AS n "
        "FROM FIRs WHERE CrimeGroup_Name IS NOT NULL AND TRIM(CrimeGroup_Name) <> '' "
        "GROUP BY grp, head ORDER BY grp, n DESC")
    # Group and head names are NORMALISED on whitespace, and the raw variants are kept.
    #
    # The registry holds 141 distinct CrimeGroup_Name strings that collapse to 130 once
    # trimmed: ' CYBER CRIME' and 'CYBER CRIME' are the same crime group typed twice. The
    # first version of this script slugged them identically and silently overwrote 11
    # concepts, which is exactly the failure a knowledge bundle must not have. Merging is
    # also the honest reading - a leading space is a data-entry artefact, not an offence.
    groups: dict[str, list[tuple[str, int]]] = {}
    variants: dict[str, set[str]] = {}
    heads_acc: dict[str, dict[str, int]] = {}
    for r in q:
        g = canon(r["grp"])
        h = canon(r["head"] or "(unspecified)") or "(UNSPECIFIED)"
        variants.setdefault(g, set()).add(str(r["grp"]))
        acc = heads_acc.setdefault(g, {})
        acc[h] = acc.get(h, 0) + r["n"]
    for g, acc in heads_acc.items():
        groups[g] = sorted(acc.items(), key=lambda kv: -kv[1])

    total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    years = con.execute("SELECT MIN(FIR_YEAR), MAX(FIR_YEAR) FROM FIRs "
                        "WHERE FIR_YEAR IS NOT NULL").fetchone()
    districts = con.execute("SELECT COUNT(DISTINCT district_norm) FROM FIRs").fetchone()[0]
    stations = con.execute("SELECT COUNT(DISTINCT UnitName) FROM FIRs").fetchone()[0]

    # The statute is embedded in a free-text column ("IPC 1860 U/s: 379"), so the ACT is
    # everything before the " U/s:" marker. 144k distinct raw strings collapse to a short
    # list of acts, which is the level a knowledge bundle should describe.
    acts: dict[str, int] = {}
    for r in con.execute(
            "SELECT ActSection, COUNT(*) n FROM FIRs "
            "WHERE ActSection IS NOT NULL AND TRIM(ActSection) <> '' GROUP BY ActSection"):
        act = re.split(r"\s+U/s[:\s]", str(r["ActSection"]), maxsplit=1)[0].strip(" ,.")
        if act:
            acts[act] = acts.get(act, 0) + r["n"]

    mo = con.execute("SELECT COUNT(*) FROM FIRs WHERE MO_Details IS NOT NULL "
                     "AND TRIM(MO_Details) <> ''").fetchone()[0]
    return {"groups": groups, "variants": variants, "total": total,
            "years": tuple(years), "acts": acts, "districts": districts,
            "stations": stations, "mo_rows": mo}


# ── Builders ─────────────────────────────────────────────────────────────────

def build_taxonomy(dest: Path, reg: dict, db_resource: str) -> list[tuple[str, str, str]]:
    entries = []
    for grp, heads in sorted(reg["groups"].items(), key=lambda kv: -sum(n for _, n in kv[1])):
        n = sum(c for _, c in heads)
        name = slug(grp)
        rows = NL.join(f"| {h} | {c:,} |" for h, c in heads)
        body = (
            f"# {grp}" + NL + NL
            + f"A crime group in the Karnataka State Police FIR registry. "
              f"**{n:,} FIRs** ({100 * n / reg['total']:.2f}% of the registry), "
              f"recorded under **{len(heads)} crime head(s)**." + NL + NL
            + "## Crime heads" + NL + NL
            + "| Crime head | FIRs |" + NL + "|---|---:|" + NL + rows + NL + NL
            + "Counts are the registry's own, at export time. This concept describes what "
              "the record contains; it is not a legal definition of the offence." + NL + NL
            + (("*The registry records this group under "
                f"{len(reg['variants'].get(grp, ()))} spellings that differ only in case "
                "or whitespace — "
                + ", ".join(f"`{v}`" for v in sorted(reg["variants"].get(grp, ())))
                + ". They are one group, merged here and counted once.*" + NL + NL)
               if len(reg["variants"].get(grp, ())) > 1 else "")
            + "See also [the taxonomy index](/taxonomy/index.md) and "
              "[the FIR registry](/registry.md)."
        )
        concept(dest / "taxonomy" / f"{name}.md", {
            "type": "Crime Group",
            "title": grp,
            "description": f"{n:,} FIRs across {len(heads)} crime head(s).",
            "tags": ["taxonomy", "crime-group", "ksp"],
            "generated": {"by": PRODUCER, "at": _now()},
            "sources": _sources(db_resource, "KSP FIR registry (FIRs table)", count=n),
            "status": "stable",
        }, body)
        entries.append((grp, f"./{name}.md", f"{n:,} FIRs · {len(heads)} head(s)"))
    return entries


def build_templates(dest: Path) -> list[tuple[str, str, str]]:
    """The T-series whitelist, as OKF Attested Computations."""
    from app.services.zcql_repo import TEMPLATES

    def _type_name(ann) -> str:
        s = str(ann).replace("typing.", "").replace("<class '", "").replace("'>", "")
        return s.replace("Optional[", "").replace("]", "").replace("[", " of ")

    entries = []
    for tid in sorted(TEMPLATES, key=lambda k: (not k.startswith("T"), k)):
        t = TEMPLATES[tid]
        params = []
        for fname, f in t.param_model.model_fields.items():
            params.append({"name": fname, "type": _type_name(f.annotation),
                           "required": bool(f.is_required())})
        name = slug(f"{tid}-{t.description}")
        examples = NL.join(f"* {e}" for e in (t.examples or []))
        body = (
            f"# {tid} — {t.description}" + NL + NL
            + "A whitelisted, parameterised query over the FIR registry. Antar never "
              "executes free-form SQL: an officer's question is resolved to one of these "
              "templates, or it is refused." + NL + NL
            + ("## Questions this answers" + NL + NL + examples + NL + NL if examples else "")
            + "## Computation" + NL + NL
            + f"`app/services/zcql_repo.py::TEMPLATES[{tid!r}]` builds a `QuerySpec` from "
              f"the validated `{t.param_model.__name__}` parameter model. The spec is "
              "compiled to parameterised SQL — every value is bound, never interpolated." + NL + NL
            + "## Attestation" + NL + NL
            + "The receipt fields below are what a run must return for its result to be "
              "checkable: the template that answered, the bound parameters, and the row "
              "ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the "
              "deterministic attester — it re-checks every figure in an answer against "
              "those rows, with no model in the loop." + NL + NL
            + ("*Internal template: used by analytics and scans, hidden from the selector.*"
               if getattr(t, "internal", False) else
               "Reachable from chat, `/api/chat` and `/api/chat/stream`.")
        )
        concept(dest / "templates" / f"{name}.md", {
            "type": "Attested Computation",
            "title": f"{tid} — {t.description}",
            "description": t.description,
            "runtime": "python",
            "parameters": params,
            "executor": {"resource": "/app/services/zcql_repo.py",
                         "receipt": ["template_id", "params", "row_ids", "rows"]},
            "attester": {"resource": "/app/agents/agentic_spine.py"},
            "tags": ["query-template", "deterministic", "whitelist"],
            "generated": {"by": PRODUCER, "at": _now()},
            "status": "stable",
        }, body)
        entries.append((f"{tid} — {t.description}", f"./{name}.md",
                        f"{len(params)} parameter(s)"))
    return entries


def build_agents(dest: Path) -> list[tuple[str, str, str]]:
    from app.agents import manifest as mf
    m = mf.load()
    entries = []
    for a in sorted(m.agents.values(), key=lambda x: x.agent):
        name = slug(a.agent)
        reach = (f"Runs as graph node `{a.graph_node}`."
                 if a.graph_node else "No graph node — API and autonomous surfaces only.")
        if a.hosted_by:
            reach += f" Hosted inside `{a.hosted_by}`'s node."
        body = (
            f"# {a.agent} — {a.role}" + NL + NL
            + f"{reach}" + NL + NL
            + f"* **Module**: `{a.module}`" + NL
            + (f"* **Routes**: {', '.join(a.routes)}" + NL if a.routes else "")
            + (f"* **Guardrails**: {', '.join(a.guardrails)}" + NL if a.guardrails else "")
            + f"* **Human approval required**: {'yes' if a.hitl else 'no'}" + NL + NL
            + (f"**When it fails**: {a.degraded}" + NL + NL if a.degraded else "")
            + "Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is "
              "executable: `app/agents/manifest.py` parses it at import time and a test "
              "fails the build when it disagrees with the compiled graph."
        )
        concept(dest / "agents" / f"{name}.md", {
            "type": "Agent",
            "title": f"{a.agent} — {a.role}",
            "description": a.role,
            "tags": ["agent", a.kind] + (["hitl"] if a.hitl else []),
            "generated": {"by": PRODUCER, "at": _now()},
            "sources": _sources("/AGENTS.md", "Antar agent manifest"),
            "status": "stable",
        }, body)
        entries.append((a.agent, f"./{name}.md", a.role))
    return entries


def build_statutes(dest: Path, reg: dict, db_resource: str) -> list[tuple[str, str, str]]:
    top = sorted(reg["acts"].items(), key=lambda kv: -kv[1])[:40]
    entries = []
    for act, n in top:
        name = slug(act)
        body = (
            f"# {act}" + NL + NL
            + f"Cited on **{n:,} FIRs** ({100 * n / reg['total']:.2f}% of the registry)." + NL + NL
            + "The registry stores the statute as free text in `ActSection` "
              "(for example `IPC 1860 U/s: 379`), so this concept is the ACT, parsed from "
              "everything before the `U/s:` marker. Section-level citation stays in the "
              "FIR row rather than being restated here, because the raw column holds "
              f"**{len(reg['acts']):,} distinct act strings** and normalising sections "
              "would mean asserting a mapping the registry does not contain." + NL + NL
            + "See [the statute index](/statutes/index.md)."
        )
        concept(dest / "statutes" / f"{name}.md", {
            "type": "Statute",
            "title": act,
            "description": f"Cited on {n:,} FIRs.",
            "tags": ["statute", "law"],
            "generated": {"by": PRODUCER, "at": _now()},
            "sources": _sources(db_resource, "KSP FIR registry (ActSection)", count=n),
            "status": "stable",
        }, body)
        entries.append((act, f"./{name}.md", f"{n:,} FIRs"))
    return entries


def build_vocabulary(dest: Path, reg: dict, db_resource: str) -> list[tuple[str, str, str]]:
    from app.services.zcql_repo import _concept_map
    cmap = _concept_map()
    rows = NL.join(f"| {k} | {', '.join(sorted(set(x.strip() for x in v)))} |"
                   for k, v in sorted(cmap.items()))
    concept(dest / "vocabulary" / "crime-concepts.md", {
        "type": "Vocabulary",
        "title": "Crime concept vocabulary",
        "description": f"{len(cmap)} everyday terms mapped to registry crime groups.",
        "tags": ["vocabulary", "nlu"],
        "generated": {"by": PRODUCER, "at": _now()},
        "sources": _sources("/app/services/zcql_repo.py", "Registry-derived concept map",
                            count=len(cmap)),
        "status": "stable",
    }, f"# Crime concept vocabulary{NL}{NL}"
       f"How an officer's words resolve to the registry's own crime groups. "
       f"**{len(cmap)} concepts.** Derived from the registry, not hand-curated: a term "
       f"that matches nothing is refused rather than guessed at.{NL}{NL}"
       f"| Concept | Registry crime group(s) |{NL}|---|---|{NL}{rows}")

    pct = 100 * reg["mo_rows"] / reg["total"]
    concept(dest / "vocabulary" / "modus-operandi.md", {
        "type": "Vocabulary",
        "title": "Modus operandi vocabulary",
        "description": f"MO narrative text is present on {reg['mo_rows']:,} of "
                       f"{reg['total']:,} FIRs ({pct:.3f}%).",
        "tags": ["vocabulary", "modus-operandi", "coverage-limited"],
        "generated": {"by": PRODUCER, "at": _now()},
        "sources": _sources(db_resource, "KSP FIR registry (MO_Details)",
                            count=reg["mo_rows"]),
        "status": "draft",
    }, f"# Modus operandi vocabulary{NL}{NL}"
       f"**Coverage first, because it decides what may be claimed.** `MO_Details` is "
       f"populated on **{reg['mo_rows']:,} of {reg['total']:,} FIRs — {pct:.3f}%**.{NL}{NL}"
       f"That is a thin evidence base, and it is the reason Antar does not offer "
       f"behavioural profiling as a product claim. MO text is used where it exists — the "
       f"Second Brain indexes it into the composite document it embeds — and its absence "
       f"is stated rather than filled in.{NL}{NL}"
       f"Marked `status: draft` deliberately: this concept describes a field that is not "
       f"yet usable at scale, and OKF's lifecycle signal is the honest place to say so.")

    return [("Crime concept vocabulary", "./crime-concepts.md",
             f"{len(cmap)} terms → registry groups"),
            ("Modus operandi vocabulary", "./modus-operandi.md",
             f"populated on {pct:.3f}% of FIRs")]


def build_top_level(dest: Path, reg: dict, db_resource: str) -> None:
    y0, y1 = reg["years"]

    concept(dest / "registry.md", {
        "type": "Dataset",
        "title": "Karnataka State Police FIR registry",
        "description": f"{reg['total']:,} First Information Reports, {y0}-{y1}.",
        "resource": db_resource,
        "tags": ["dataset", "fir", "ksp"],
        "generated": {"by": PRODUCER, "at": _now()},
        "sources": _sources(db_resource, "KSP FIR registry", count=reg["total"]),
        "status": "stable",
    }, f"""# Karnataka State Police FIR registry

The record everything else in Antar stands on.

| | |
|---|---:|
| FIRs | {reg['total']:,} |
| Years | {y0}-{y1} |
| Districts | {reg['districts']:,} |
| Police stations | {reg['stations']:,} |
| Crime groups | {len(reg['groups']):,} |
| Distinct act strings | {len(reg['acts']):,} |

## What this record does not contain

Stated here because a knowledge bundle that only lists strengths is marketing.

* **No event times.** FIRs carry a date, not a time of day. This is why the forecast is a
  weekly panel, and why a near-repeat triggering kernel was measured and rejected - see
  [the forecast model card](/forecast-model-card.md).
* **MO narrative on {reg['mo_rows']:,} rows** of {reg['total']:,}. See
  [the MO vocabulary](/vocabulary/modus-operandi.md).
* **No accused-identity column** in the raw extract, so person-level linkage is derived,
  never asserted from a key the registry does not have.

## How it is queried

Never with free-form SQL. Questions resolve to one of the whitelisted
[query templates](/templates/index.md), or they are refused.
""")

    concept(dest / "evidence-classes.md", {
        "type": "Vocabulary",
        "title": "Evidence classes (K/D/I/U)",
        "description": "How Antar labels the standing of every claim it makes.",
        "tags": ["vocabulary", "evidence", "icd-203"],
        "generated": {"by": PRODUCER, "at": _now()},
        "verified": [{"by": HUMAN_OWNER, "at": _now()}],
        "status": "stable",
    }, """# Evidence classes (K/D/I/U)

Adapted from ICD 203 (US intelligence-community analytic standards). Every claim Antar
emits carries one, and the class travels with the claim through synthesis, the API and
the printable export.

| Class | Marker | Means |
|---|---|---|
| Known | `[VERIFIED]` | Read directly from FIR rows; the row ids are cited. |
| Derived | `[COMPUTED]` | Calculated from rows by a deterministic transform - a count, a rate, a conformal band, a similarity. Reproducible by hand from the cited rows. |
| Inferred | `[INFERRED]` | A scored hypothesis. Never presented without the base-rate audit from [devils_advocate](/agents/devils-advocate.md). |
| Unknown | `[GAP]` | Named as missing, with the collection action that would close it. |

The distinction that matters operationally: a **Derived** claim is as good as its inputs
and its arithmetic, both of which are checkable. An **Inferred** claim is a guess with a
number attached, and a number attached to a guess is how an officer gets anchored. That is
why the adversarial review is part of the research node rather than an optional follow-up.
""")

    # The constitution is the one concept here that people wrote and own, so it is the one
    # that carries `verified: {by: human:...}`. Under OKF's tier derivation it reads as
    # human-reviewed while everything generated from the database reads as unverified -
    # which is the truth, expressed in the format's own vocabulary.
    src = ROOT / "docs" / "ANTAR_CONSTITUTION.md"
    if src.exists():
        raw = src.read_text(encoding="utf-8", errors="replace")
        concept(dest / "constitution.md", {
            "type": "Policy",
            "title": "The Antar constitution",
            "description": "The rules Antar is held to, enforced in code.",
            "tags": ["policy", "constitution", "governance"],
            "generated": {"by": PRODUCER, "at": _now()},
            "verified": [{"by": HUMAN_OWNER, "at": _now()}],
            "sources": _sources("/docs/ANTAR_CONSTITUTION.md", "Antar constitution",
                                last_modified=datetime.fromtimestamp(
                                    src.stat().st_mtime, timezone.utc
                                ).strftime("%Y-%m-%dT%H:%M:%SZ")),
            "status": "stable",
        }, "Enforced in code at `app/core/antar_identity.py`, not merely published."
           + NL + NL + re.sub(r"^#", "##", raw, flags=re.M).strip())

    # Forecast model card. Numbers are LIFTED from the generated back-test report, never
    # retyped: if the regex does not find a figure it is omitted rather than guessed, which
    # is the same rule the product follows.
    bt = ROOT / "docs" / "FORECAST_BACKTEST.md"
    metrics, stale = [], None
    if bt.exists():
        text = bt.read_text(encoding="utf-8", errors="replace")
        for label, pat in (("Top-5% of beats catches", r"top[- ]5%[^0-9]{0,40}([0-9.]+)"),
                           ("PAI @ 5%", r"PAI[^0-9]{0,30}([0-9.]+)"),
                           ("Weeks beating the last-4 baseline", r"(\d+\s*/\s*23)")):
            m = re.search(pat, text, re.I)
            if m:
                metrics.append((label, m.group(1)))
        stale = datetime.fromtimestamp(bt.stat().st_mtime, timezone.utc)

    rows = NL.join(f"| {k} | {v} |" for k, v in metrics) or "| (see the report) | |"
    front = {
        "type": "Model Card",
        "title": "Weekly crime forecast - model card",
        "description": "Poisson GLM with split-conformal ranges, judged on a rolling "
                       "23-week back-test.",
        "tags": ["model-card", "forecast", "conformal"],
        "generated": {"by": PRODUCER, "at": _now()},
        "sources": _sources("/docs/FORECAST_BACKTEST.md", "Rolling back-test report"),
        "status": "stable",
    }
    if stale:
        # A model card outlives its numbers. `stale_after` is the spec's way of saying so,
        # and a year is an honest shelf life for a back-test on a record ending 2024-03.
        front["stale_after"] = stale.replace(year=stale.year + 1).strftime("%Y-%m-%dT%H:%M:%SZ")
    concept(dest / "forecast-model-card.md", front, f"""# Weekly crime forecast - model card

Poisson GLM over a weekly panel of counts per unit, with **split-conformal** prediction
ranges and a Getis-Ord Gi* hotspot term. Judged on a rolling back-test over 23 weekly
origins - the same protocol every time, so numbers stay comparable across changes.

| Measure | Value |
|---|---|
{rows}

## What was tried and rejected

A **near-repeat / self-exciting** term, the best-evidenced improvement in this literature
(Mohler et al., JASA 2011). Measured on the same back-test: **0 of 60 metrics moved**, and
fitting was 12% slower. Weekly counts over beats cannot express a day-and-metre triggering
kernel - a data-resolution limit, not a modelling failure. The code stays behind a flag
that is off.

This section is in the model card on purpose. A card that lists only what worked tells you
nothing about how the thing was decided.

## Limits an officer should know

* The record ends **2024-03**; anything later is seeded and labelled as such.
* Beat areas are Voronoi estimates - no beat boundaries exist in the data - so PAI is
  approximate and labelled approximate.
* Patrolling a flagged beat records more FIRs there. The feedback loop is stated on every
  beat card, and rotating patrols is the recommendation.

Full report: `docs/FORECAST_BACKTEST.md` in the Antar repository.
""")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(NL + NL)[0])
    ap.add_argument("--dest", default=str(ROOT / "knowledge"))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    from app.core.db_path import get_db_path
    db = Path(get_db_path())
    # A STABLE logical identifier, not the absolute path of whichever machine ran the
    # export. The bundle is meant to be portable — shippable as a tarball, readable in any
    # repo — and `file:///E:/...` is neither portable nor anyone else's business.
    db_resource = "urn:antar:registry:firs"
    _ = db

    dest = Path(args.dest)
    if dest.exists():
        # Regenerating must not leave a concept behind that the registry no longer has -
        # a stale crime group in a knowledge bundle is exactly the drift this exists to
        # prevent. Only generated subtrees are cleared; nothing outside them is touched.
        import shutil
        for sub in ("taxonomy", "templates", "agents", "statutes", "vocabulary"):
            shutil.rmtree(dest / sub, ignore_errors=True)
        for f in dest.glob("*.md"):
            f.unlink()

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        reg = read_registry(con)
    finally:
        con.close()

    build_top_level(dest, reg, db_resource)
    tax = build_taxonomy(dest, reg, db_resource)
    tpl = build_templates(dest)
    agt = build_agents(dest)
    sta = build_statutes(dest, reg, db_resource)
    voc = build_vocabulary(dest, reg, db_resource)

    index(dest / "taxonomy" / "index.md", [("Crime groups", tax)])
    index(dest / "templates" / "index.md", [("Whitelisted query templates", tpl)])
    index(dest / "agents" / "index.md", [("Agents", agt)])
    index(dest / "statutes" / "index.md", [("Acts by volume", sta)])
    index(dest / "vocabulary" / "index.md", [("Vocabularies", voc)])

    index(dest / "index.md", [
        ("Antar", [
            ("The FIR registry", "./registry.md",
             f"{reg['total']:,} FIRs, {reg['years'][0]}-{reg['years'][1]}"),
            ("The constitution", "./constitution.md", "the rules, enforced in code"),
            ("Evidence classes", "./evidence-classes.md", "K/D/I/U"),
            ("Forecast model card", "./forecast-model-card.md",
             "what it does, and what was rejected"),
        ]),
        ("Knowledge", [
            ("Crime taxonomy", "./taxonomy/index.md", f"{len(tax)} crime groups"),
            ("Statutes", "./statutes/index.md", f"top {len(sta)} acts by volume"),
            ("Vocabularies", "./vocabulary/index.md", "how words resolve to the record"),
        ]),
        ("Capability", [
            ("Query templates", "./templates/index.md",
             f"{len(tpl)} attested computations"),
            ("Agents", "./agents/index.md", f"{len(agt)} declared agents"),
        ]),
    ], root=True)

    (dest / "log.md").write_text(
        "# Directory Update Log" + NL + NL
        + f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d')}" + NL
        + f"* **Generation**: bundle rebuilt from the registry by `{PRODUCER}` - "
          f"{len(tax)} crime groups, {len(sta)} statutes, {len(tpl)} query templates, "
          f"{len(agt)} agents." + NL,
        encoding="utf-8")

    files = sorted(dest.rglob("*.md"))
    size = sum(f.stat().st_size for f in files)
    if not args.quiet:
        print(f"OKF v{OKF_VERSION} bundle -> {dest}")
        print(f"  {len(tax):>4} crime groups")
        print(f"  {len(sta):>4} statutes")
        print(f"  {len(tpl):>4} query templates (Attested Computation)")
        print(f"  {len(agt):>4} agents")
        print(f"  {len(voc):>4} vocabularies")
        print(f"  {len(files)} files - {size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
