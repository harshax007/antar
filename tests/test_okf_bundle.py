"""
The OKF v0.2 knowledge bundle (final_backend.md §6 P2-1).

Two jobs, and the second is the one that matters.

**Conformance** — the bundle is a valid OKF bundle: parseable frontmatter, a non-empty
`type` on every concept, reserved filenames behaving as the spec says.

**Drift** — the bundle still describes the system that is actually running. A knowledge
bundle is a claim about the product, and a stale claim is worse than no claim: it reads as
authoritative while being wrong. So these tests compare the committed `knowledge/` against
the live database, the live template registry and the live agent manifest, and fail when
they disagree. That is the same contract `AGENTS.md` holds itself to.

If one of these fails, the fix is almost never to edit the bundle. It is:

    python scripts/build_okf_bundle.py
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from scripts.build_okf_bundle import canon

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "knowledge"
RESERVED = {"index.md", "log.md"}

pytestmark = pytest.mark.skipif(
    not BUNDLE.exists(),
    reason="knowledge/ not generated — run scripts/build_okf_bundle.py")


def concepts() -> list[Path]:
    return [p for p in sorted(BUNDLE.rglob("*.md")) if p.name not in RESERVED]


def front(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path} has no frontmatter block"
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def title_set(folder: str) -> set[str]:
    return {front(p).get("title") for p in (BUNDLE / folder).glob("*.md")
            if p.name not in RESERVED}


# ── Conformance (OKF v0.2 §11) ───────────────────────────────────────────────

def test_every_concept_has_parseable_frontmatter_with_a_type():
    """The entire conformance bar: parseable YAML, non-empty `type`."""
    for p in concepts():
        fm = front(p)
        assert isinstance(fm, dict), f"{p}: frontmatter is not a mapping"
        assert str(fm.get("type", "")).strip(), f"{p}: missing or empty `type`"


def test_bundle_declares_its_version_at_the_root_only():
    root = BUNDLE / "index.md"
    assert root.exists()
    assert yaml.safe_load(root.read_text(encoding="utf-8").split("---", 2)[1])["okf_version"] == "0.2"
    # §9: no other index.md may carry frontmatter at all.
    for p in BUNDLE.rglob("index.md"):
        if p != root:
            assert not p.read_text(encoding="utf-8").startswith("---"), \
                f"{p}: only the bundle-root index.md may carry frontmatter"


def test_trust_signals_use_the_actor_convention():
    """`human:` is a claim that a person reviewed this. It must not be used loosely.

    OKF consumers derive their trust tier from the prefix, so machine-generated content
    carrying `human:` would launder a generated concept into a reviewed one.
    """
    for p in concepts():
        fm = front(p)
        gen = fm.get("generated") or {}
        if gen:
            assert not str(gen.get("by", "")).startswith("human:"), \
                f"{p}: generated content must not claim a human actor"
            assert str(gen.get("by", "")).startswith(("process:", "human:")) or "/" in str(gen.get("by")), \
                f"{p}: `generated.by` does not follow the actor convention"
        for v in (fm.get("verified") or []):
            assert v.get("by") and v.get("at"), f"{p}: a verified entry needs by and at"


def test_only_human_authored_concepts_claim_human_review():
    """Exactly the concepts people actually own are marked human-reviewed."""
    reviewed = {p.name for p in concepts() if front(p).get("verified")}
    assert reviewed == {"constitution.md", "evidence-classes.md"}, (
        "the set of human-reviewed concepts changed — if that is intended, update this "
        f"test deliberately rather than letting it drift: {sorted(reviewed)}")


def test_internal_links_resolve():
    """A broken link does not break conformance, but it does break usefulness."""
    broken = []
    for p in sorted(BUNDLE.rglob("*.md")):
        body = p.read_text(encoding="utf-8")
        for href in re.findall(r"\]\((\.?/[^)]+\.md)\)", body):
            target = (BUNDLE / href.lstrip("/")) if href.startswith("/") else (p.parent / href)
            if not target.resolve().exists():
                broken.append(f"{p.relative_to(BUNDLE)} -> {href}")
    assert not broken, "unresolved links: " + "; ".join(broken[:10])


# ── Drift: the bundle vs the running system ──────────────────────────────────

def test_taxonomy_matches_the_database():
    """Every crime group in the registry has a concept, and vice versa."""
    from app.core.db_path import get_db_path
    con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True)
    try:
        # Canonicalised exactly as the generator does. The registry records the same
        # group under several spellings (case and whitespace); comparing raw strings here
        # would assert the duplication rather than the taxonomy.
        db_groups = {canon(r[0]) for r in con.execute(
            "SELECT DISTINCT CrimeGroup_Name FROM FIRs "
            "WHERE CrimeGroup_Name IS NOT NULL AND TRIM(CrimeGroup_Name) <> ''")}
    finally:
        con.close()

    bundled = title_set("taxonomy")
    missing = db_groups - bundled
    extra = bundled - db_groups
    assert not missing, f"registry has groups the bundle does not: {sorted(missing)[:10]}"
    assert not extra, f"bundle has groups the registry does not: {sorted(extra)[:10]}"


def test_every_crime_head_appears_under_its_group():
    """Heads are sections rather than separate files, so assert they are all present."""
    from app.core.db_path import get_db_path
    con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT DISTINCT CrimeGroup_Name, CrimeHead_Name FROM FIRs "
            "WHERE CrimeGroup_Name IS NOT NULL AND TRIM(CrimeGroup_Name) <> '' "
            "AND CrimeHead_Name IS NOT NULL AND TRIM(CrimeHead_Name) <> ''").fetchall()
    finally:
        con.close()

    by_group: dict[str, set[str]] = {}
    for grp, head in rows:
        by_group.setdefault(canon(grp), set()).add(canon(head))

    text_by_title = {front(p).get("title"): p.read_text(encoding="utf-8")
                     for p in (BUNDLE / "taxonomy").glob("*.md") if p.name not in RESERVED}
    missing = []
    for grp, heads in by_group.items():
        body = text_by_title.get(grp, "")
        for h in heads:
            if f"| {h} |" not in body:
                missing.append(f"{grp} / {h}")
    assert not missing, f"{len(missing)} crime head(s) missing from the bundle: {missing[:8]}"


def test_templates_match_the_live_registry():
    from app.services.zcql_repo import TEMPLATES
    bundled = {t.split(" — ")[0] for t in title_set("templates")}
    assert bundled == set(TEMPLATES), (
        f"bundle vs registry mismatch — only in bundle: {sorted(bundled - set(TEMPLATES))}, "
        f"only in registry: {sorted(set(TEMPLATES) - bundled)}")


def test_template_parameters_match_their_pydantic_models():
    """The parameters are the callable interface, so a silent change matters."""
    from app.services.zcql_repo import TEMPLATES
    for p in (BUNDLE / "templates").glob("*.md"):
        if p.name in RESERVED:
            continue
        fm = front(p)
        tid = str(fm["title"]).split(" — ")[0]
        expected = set(TEMPLATES[tid].param_model.model_fields)
        got = {x["name"] for x in fm.get("parameters", [])}
        assert got == expected, f"{tid}: parameters drifted — bundle {sorted(got)}, code {sorted(expected)}"


def test_templates_are_attested_computations_with_a_receipt():
    """The point of the type: a run is checkable, by a deterministic attester."""
    for p in (BUNDLE / "templates").glob("*.md"):
        if p.name in RESERVED:
            continue
        fm = front(p)
        assert fm["type"] == "Attested Computation"
        assert fm.get("runtime"), f"{p}: `runtime` is REQUIRED for an Attested Computation"
        assert fm["executor"]["receipt"], f"{p}: a receipt is what makes the run checkable"
        attester = ROOT / str(fm["attester"]["resource"]).lstrip("/")
        assert attester.exists(), f"{p}: attester {attester} does not exist"


def test_agents_match_the_manifest():
    from app.agents import manifest as mf
    declared = set(mf.load().agents)
    bundled = {str(front(p).get("title")).split(" — ")[0]
               for p in (BUNDLE / "agents").glob("*.md") if p.name not in RESERVED}
    assert bundled == declared, (
        f"only in bundle: {sorted(bundled - declared)}, "
        f"only in manifest: {sorted(declared - bundled)}")


def test_registry_headline_count_matches_the_database():
    """The bundle's headline FIR count, against the registry as this session found it.

    Deliberately NOT a live `SELECT COUNT(*)`. The suite runs against the real main.db and
    `test_ingestion_csv_mapping` genuinely inserts a row, removed only when the session
    fixture tears down - so mid-run the live count is the registry plus whatever the suite
    is currently holding. Asserting the raw count made this pass alone and fail in the full
    suite, which is a flaky test rather than a drift detector.
    """
    import tests.conftest as conftest
    total = conftest.BASELINE_FIR_COUNT
    if total is None:                     # not inside the session fixture - read it live
        from app.core.db_path import get_db_path
        con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True)
        try:
            total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        finally:
            con.close()
    body = (BUNDLE / "registry.md").read_text(encoding="utf-8")
    assert f"{total:,}" in body, (
        f"registry.md does not state the registry FIR count ({total:,}) - "
        "regenerate the bundle")


def test_the_mo_coverage_claim_is_the_real_one():
    """The bundle's most uncomfortable number, asserted against the database.

    MO coverage is the limit that bounds what Antar may claim about behaviour. If this
    ever drifts upward silently, the honesty of several other claims goes with it.
    """
    from app.core.db_path import get_db_path
    con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM FIRs WHERE MO_Details IS NOT NULL "
                        "AND TRIM(MO_Details) <> ''").fetchone()[0]
    finally:
        con.close()
    body = (BUNDLE / "vocabulary" / "modus-operandi.md").read_text(encoding="utf-8")
    assert f"{n:,}" in body, f"MO coverage drifted — database says {n:,}"
