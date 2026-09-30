"""
Zero-assumption guard — a named entity that isn't in the rows must never be
presented as if it were answered.

The dangerous case is NOT "no rows" (already covered by the `no_results` contract).
It is: officer asks about entity X, the template returns rows about something else,
and the system answers confidently from them. For an evidentiary product that means
describing the wrong person. This is enforced deterministically AFTER composition,
so it holds even when the LLM ignores its instructions or is offline (rulebook #7).
"""

import asyncio

import pytest

from app.agents.query_agent import (
    NOT_FOUND_EN,
    NOT_FOUND_KN,
    ungrounded_entity,
    query_agent_run,
)


class TestUngroundedEntity:
    def test_returns_term_when_named_entity_absent_from_rows(self):
        rows = [{"suspect_id": "S0001", "full_name": "Raju K.", "alias": "Yellappa"}]
        assert ungrounded_entity({"name_or_alias": "Saleem Malik"}, rows) == "Saleem Malik"

    def test_none_when_entity_present(self):
        rows = [{"suspect_id": "S0001", "full_name": "Raju K.", "alias": "Yellappa"}]
        assert ungrounded_entity({"name_or_alias": "Raju"}, rows) is None

    def test_matches_case_insensitively_and_across_any_column(self):
        rows = [{"suspect_id": "S0001", "alias": "YELLAPPA"}]
        assert ungrounded_entity({"name_or_alias": "yellappa"}, rows) is None

    def test_checks_suspect_id_and_fir_number_too(self):
        rows = [{"suspect_id": "S0001", "fir_number": "2025-MYS-0089"}]
        assert ungrounded_entity({"suspect_id": "S9999"}, rows) == "S9999"
        assert ungrounded_entity({"fir_number": "2025-MYS-0089"}, rows) is None

    def test_empty_rows_defers_to_no_results_contract(self):
        """No rows is a different (already-handled) state — don't double-report it."""
        assert ungrounded_entity({"name_or_alias": "Saleem Malik"}, []) is None

    def test_ignores_non_entity_params(self):
        rows = [{"zone": "Rajajinagar", "crime_type": "theft"}]
        assert ungrounded_entity({"zones": ["Jayanagar"], "limit": 10}, rows) is None

    def test_is_pure_no_llm_required(self):
        """Must work with the LLM down — it takes no client and does no I/O."""
        rows = [{"full_name": "Raju K."}]
        for _ in range(3):
            assert ungrounded_entity({"name_or_alias": "Nobody"}, rows) == "Nobody"


class TestIdentifierInQuestion:
    """The reachable failure: the selector DROPS the id and picks a broad template,
    so rows come back about other people. Params can't see it; the question can."""

    def test_flags_suspect_id_missing_from_rows(self):
        rows = [{"suspect_id": "S0001", "full_name": "Raju K."}]
        assert ungrounded_entity({}, rows, "is S9999 linked to Rajajinagar theft?") == "S9999"

    def test_silent_when_id_present(self):
        rows = [{"suspect_id": "S0001", "full_name": "Raju K."}]
        assert ungrounded_entity({}, rows, "what is S0001 linked to?") is None

    def test_flags_fir_and_vehicle_identifiers(self):
        rows = [{"fir_number": "2025-BLR-0001", "vehicle": "KA05XY9999"}]
        assert ungrounded_entity({}, rows, "show FIR 2025-MYS-0089") == "2025-MYS-0089"
        assert ungrounded_entity({}, rows, "who owns KA01AB1234") == "KA01AB1234"

    def test_no_false_positive_on_ordinary_words(self):
        """Plain questions must never trip the guard — nagging on valid answers is worse."""
        rows = [{"zone": "Rajajinagar", "crime_type": "theft", "n": 12}]
        for q in ("how many thefts in Rajajinagar",
                  "chain snatching trend this year",
                  "top hotspots in Bengaluru"):
            assert ungrounded_entity({}, rows, q) is None, q


class TestGuardAppliedToAnswer:
    """End-to-end: a lying LLM must not survive the deterministic guard."""

    def _run_with_id(self, compose, lang="en"):
        from tests.test_query_agent import fake_select  # reuse the existing stub
        # T1 returns real rows for this zone/type, but the officer named S9999,
        # which the selector dropped — exactly the dangerous middle case.
        return asyncio.run(query_agent_run(
            "is S9999 involved in chain snatching in Rajajinagar", lang=lang,
            select_llm=fake_select("T1", {"crime_types": ["chain_snatching"],
                                          "zones": ["Rajajinagar"]}),
            compose_llm=compose,
        ))

    def test_rows_exist_so_this_test_is_not_vacuous(self):
        async def compose(*a, **k):
            return "Composed answer from rows."
        out = self._run_with_id(compose)
        assert out["rows"], "precondition: this scenario must return rows"

    def test_answer_leads_with_not_found_even_if_llm_claims_a_match(self):
        async def lying_compose(*a, **k):
            return "S9999 is a repeat offender operating in Rajajinagar."
        out = self._run_with_id(lying_compose)
        assert out["entity_not_found"] == "S9999"
        assert out["answer"].startswith(NOT_FOUND_EN.format(term="S9999"))
        assert "related context" in out["answer"]

    def test_kannada_lead_when_lang_kn(self):
        async def lying_compose(*a, **k):
            return "S9999 ಒಬ್ಬ ಅಪರಾಧಿ."
        out = self._run_with_id(lying_compose, lang="kn")
        assert out["answer"].startswith(NOT_FOUND_KN.format(term="S9999"))

    def test_grounding_step_recorded_in_reasoning(self):
        async def compose(*a, **k):
            return "Composed answer from rows."
        out = self._run_with_id(compose)
        assert "grounding" in [r["step"] for r in out["reasoning"]]

    def test_grounded_query_is_untouched(self):
        """A real match must NOT get the not-found lead."""
        from tests.test_query_agent import fake_select
        async def compose(*a, **k):
            return "Composed answer from rows."
        out = asyncio.run(query_agent_run(
            "chain snatching in Rajajinagar", lang="en",
            select_llm=fake_select("T1", {"crime_types": ["chain_snatching"],
                                          "zones": ["Rajajinagar"]}),
            compose_llm=compose,
        ))
        assert not out.get("entity_not_found")
        assert not out["answer"].startswith("No record matching")
