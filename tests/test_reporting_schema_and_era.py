"""Tests for the shared editor↔writer vocabulary (known issue 8), the pre-TEG-8
era leak (known issue 1), and the arc-payload weighting (known issue 12).

The schema tests exist because the close-finish hard rule was stated in prose for
four TEGs and violated on both the TEGs it applied to, silently. These assert the
collision is now a *validation error*, not a matter of the model's cooperation.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

import pydantic

from teg_analysis.reporting.story_plan import (
    CLOSE_FINISH_VEHICLES,
    NARRATIVE_STRUCTURES,
    PALETTE_VEHICLES,
    PROMINENT_VEHICLE_CHOICES,
    SYSTEM_PROMPT,
    StoryPlan,
    check_plan_consistency,
)


def _plan(**kw) -> StoryPlan:
    base = dict(
        title="t", title_candidates=[], theme="x", tone="house",
        narrative_structure="in_medias_res", opening_hook="h",
        narrative_vehicles=["counterfactual", "inversion"],
        foreshadow=[], competitions=[], rounds=[], players=[],
        must_include_beat_ids=[], cuts=[], venue_notes="",
        prominent_vehicle="counterfactual", prominent_palette="decisive_moment",
    )
    base.update(kw)
    return StoryPlan(**base)


# ---------------------------------------------------------------------------
# The exact bug: a palette value in the vehicle field
# ---------------------------------------------------------------------------
def test_palette_value_rejected_as_prominent_vehicle():
    """`decisive_moment` is a palette term; it was accepted here for 4 TEGs."""
    with pytest.raises(pydantic.ValidationError):
        _plan(prominent_vehicle="decisive_moment")


def test_vehicle_value_rejected_as_prominent_palette():
    """The mirror error — the two vocabularies are now genuinely disjoint."""
    with pytest.raises(pydantic.ValidationError):
        _plan(prominent_palette="counterfactual")


def test_the_two_vocabularies_do_not_overlap():
    assert not set(PROMINENT_VEHICLE_CHOICES) & set(PALETTE_VEHICLES)


def test_free_form_narrative_structure_rejected():
    """TEGs 11 and 14 returned whole sentences here."""
    with pytest.raises(pydantic.ValidationError):
        _plan(narrative_structure="in_medias_res — open at R4 H6 (the decisive hole)")


def test_observed_structure_values_all_valid():
    """Values seen in real published plans must remain expressible."""
    for value in ("chronological", "in_medias_res", "theme_led", "player_by_player"):
        assert value in NARRATIVE_STRUCTURES
        _plan(narrative_structure=value)


def test_unknown_vehicle_rejected():
    with pytest.raises(pydantic.ValidationError):
        _plan(narrative_vehicles=["counterfactual", "invented_vehicle_name"])


def test_inevitability_cannot_be_prominent():
    """Documented as a supporting vehicle only; now enforced."""
    assert "inevitability" not in PROMINENT_VEHICLE_CHOICES
    with pytest.raises(pydantic.ValidationError):
        _plan(prominent_vehicle="inevitability")


def test_both_prominence_fields_are_required():
    for missing in ("prominent_vehicle", "prominent_palette"):
        kwargs = {
            "title": "t", "title_candidates": [], "theme": "x", "tone": "house",
            "narrative_structure": "chronological", "opening_hook": "h",
            "foreshadow": [], "competitions": [], "rounds": [], "players": [],
            "must_include_beat_ids": [], "cuts": [], "venue_notes": "",
            "prominent_vehicle": "counterfactual",
            "prominent_palette": "decisive_moment",
        }
        del kwargs[missing]
        with pytest.raises(pydantic.ValidationError):
            StoryPlan(**kwargs)


# ---------------------------------------------------------------------------
# The prompt is generated from the same constants
# ---------------------------------------------------------------------------
def test_prompt_menus_are_generated_from_the_constants():
    for vehicle in PROMINENT_VEHICLE_CHOICES:
        assert f"`{vehicle}`" in SYSTEM_PROMPT, vehicle
    for palette in PALETTE_VEHICLES:
        assert f"`{palette}`" in SYSTEM_PROMPT, palette
    for structure in NARRATIVE_STRUCTURES:
        assert f"`{structure}`" in SYSTEM_PROMPT, structure


def test_prompt_has_no_unfilled_placeholders():
    for placeholder in ("{STRUCTURE_MENU}", "{VEHICLE_MENU}", "{PALETTE_MENU}"):
        assert placeholder not in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Combination checks the schema can't express
# ---------------------------------------------------------------------------
def test_close_finish_violation_is_reported():
    bundle = {"tournament_shape": {"close_finish": True}, "beats": []}
    warnings = check_plan_consistency(
        _plan(prominent_vehicle="hero_arc", narrative_vehicles=["hero_arc"]), bundle)
    assert any("close_finish" in w for w in warnings)


def test_close_finish_compliance_is_silent():
    bundle = {"tournament_shape": {"close_finish": True}, "beats": []}
    for vehicle in CLOSE_FINISH_VEHICLES:
        assert check_plan_consistency(
            _plan(prominent_vehicle=vehicle, narrative_vehicles=[vehicle]), bundle) == []


def test_prominent_vehicle_must_appear_in_the_vehicle_list():
    bundle = {"tournament_shape": {"close_finish": False}, "beats": []}
    warnings = check_plan_consistency(
        _plan(prominent_vehicle="motif", narrative_vehicles=["counterfactual"]), bundle)
    assert any("not in" in w for w in warnings)


def test_dropped_mandatory_beat_is_reported():
    bundle = {"tournament_shape": {}, "beats": [{"id": "b01", "mandatory": True}]}
    assert any("mandatory" in w for w in check_plan_consistency(_plan(), bundle))


def test_mandatory_beat_in_cuts_is_reported():
    bundle = {"tournament_shape": {}, "beats": [{"id": "b01", "mandatory": True}]}
    warnings = check_plan_consistency(
        _plan(must_include_beat_ids=["b01"], cuts=["b01"]), bundle)
    assert any("cuts" in w for w in warnings)


# ---------------------------------------------------------------------------
# Round plan is no longer a generation behind (known issue 3)
# ---------------------------------------------------------------------------
def test_round_plan_shares_the_tournament_vocabulary():
    from teg_analysis.reporting.round_report import RoundStoryPlan
    fields = RoundStoryPlan.model_fields
    for name in ("narrative_vehicles", "prominent_vehicle", "prominent_palette", "payoffs"):
        assert name in fields, name


def test_round_prompt_menus_are_rendered():
    from teg_analysis.reporting.round_report import ROUND_PLAN_SYSTEM
    for placeholder in ("{STRUCTURE_MENU}", "{VEHICLE_MENU}", "{PALETTE_MENU}"):
        assert placeholder not in ROUND_PLAN_SYSTEM
    assert "`counterfactual`" in ROUND_PLAN_SYSTEM


# ---------------------------------------------------------------------------
# Era leak (known issue 1)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("teg_num,expected,forbidden", [
    (5, "netvp", "stableford"),      # net-vs-par era
    (9, "stableford", "netvp"),      # Stableford era
])
def test_hole_evidence_is_era_aware(teg_num, expected, forbidden):
    from teg_analysis.reporting.events import build_notable_events
    events = build_notable_events(teg_num)
    keys = {k for e in events for h in e.holes for k in h}
    assert expected in keys
    assert forbidden not in keys


def test_pre_teg8_hot_stretch_headline_avoids_stableford_points():
    """TEGs 5-7 narrated a net-vs-par race in Stableford points, in published prose."""
    from teg_analysis.reporting.events import build_notable_events
    for e in build_notable_events(5):
        if e.type == "hot_stretch":
            assert "points" not in e.headline, e.headline


# ---------------------------------------------------------------------------
# Arc payload weighting (known issue 12)
# ---------------------------------------------------------------------------
def test_arcs_carry_a_weighted_change_summary():
    from teg_analysis.reporting.events import build_notable_events
    events = build_notable_events(18)
    trophy = next(e for e in events if e.type == "trophy_win").context["arc"]
    spoon = next(e for e in events if e.type == "wooden_spoon").context["arc"]

    summary = trophy["lead_change_summary"]
    assert set(summary) >= {"total", "early_round1", "final_round", "outright",
                            "decisive", "all_routine"}
    # TEG 18's entire lead-change story is three R1 changes — the case that got
    # framed as "chaos" off a bare count.
    assert summary["all_routine"] is True
    assert all("significance" in c for c in trophy["lead_changes"])

    # The Spoon arc had no outright/level distinction at all before this.
    assert all("outright" in c and "significance" in c for c in spoon["bottom_changes"])
    assert "bottom_change_summary" in spoon


def test_long_held_lead_lost_detector_fires_but_is_rare():
    from teg_analysis.reporting.events import build_notable_events
    counts = {}
    for teg_num in (10, 11, 14):
        beats = [e for e in build_notable_events(teg_num) if e.type == "long_lead_lost"]
        counts[teg_num] = len(beats)
        for beat in beats:
            assert beat.context["tenure_holes"] >= 18
    assert counts[11] >= 1        # Jon Baker held the Trophy lead 45 holes
    assert all(n <= 2 for n in counts.values())   # rare, not spam


# ---------------------------------------------------------------------------
# Selection weights (known issue 13) — adopted 2026-08-11
# ---------------------------------------------------------------------------
def test_default_weights_are_the_adopted_setting():
    """`balanced` is what every call site uses; it must be the chosen setting.

    Guards against a silent revert to (1,1,1), which produced a cut that was
    53% blow-ups and 60% disaster-toned.
    """
    from teg_analysis.reporting.scoring import MODE_WEIGHTS
    assert MODE_WEIGHTS["balanced"] == (1.5, 0.8, 0.7)
    assert MODE_WEIGHTS["fast"] == MODE_WEIGHTS["balanced"]


def test_default_weights_reduce_the_blow_up_share():
    """End-to-end: the adopted weights must actually move the mix."""
    from teg_analysis.reporting.events import build_notable_events
    from teg_analysis.reporting.scoring import MODE_WEIGHTS, total_score

    events = build_notable_events(16)          # worst case under the old default
    def share(weights):
        ranked = sorted(events, key=lambda e: total_score(e, weights), reverse=True)
        top = ranked[:20]
        return sum(1 for e in top if e.type == "big_blowup") / len(top)

    assert share(MODE_WEIGHTS["balanced"]) < share((1.0, 1.0, 1.0))


# ---------------------------------------------------------------------------
# C2 / D1 prompt separation
# ---------------------------------------------------------------------------
def test_writer_prompt_is_composed_from_separable_blocks():
    """Voice (C2) and faithfulness (D1) are separate constants, not one literal.

    They still concatenate into one prompt — the split is so a voice experiment
    cannot accidentally edit a guardrail, which is exactly the risk of keeping
    16k characters of both in a single string.
    """
    from teg_analysis.reporting.authoring import (
        WRITER_SYSTEM, WRITER_VOICE, WRITER_FAITHFULNESS, WRITER_OUTPUT_RULE)
    assert WRITER_SYSTEM == WRITER_VOICE + "\n" + WRITER_FAITHFULNESS + "\n" + WRITER_OUTPUT_RULE
    # The blocks own distinct content.
    assert "VOICE:" in WRITER_VOICE and "FAITHFULNESS" not in WRITER_VOICE
    assert WRITER_FAITHFULNESS.startswith("FAITHFULNESS (non-negotiable):")
    assert "countback" in WRITER_FAITHFULNESS


def test_faithfulness_rules_that_trace_to_incidents_are_still_present():
    """Guards against quietly dropping a rule while tuning voice.

    Each of these traces to an observed failure. D3 also checks several of them,
    but prevention and detection are kept together deliberately.
    """
    from teg_analysis.reporting.authoring import WRITER_FAITHFULNESS
    for phrase in ("countback", "same hole", "a week", "Arithmetic must be exact",
                   "player_relationships", "beat ID"):
        assert phrase.lower() in WRITER_FAITHFULNESS.lower(), phrase


def test_writer_reads_the_right_prominence_field_for_the_palette():
    """The PALETTE block must point at `prominent_palette`, not `prominent_vehicle`.

    Regression guard for the same class of bug as known issue 8: the writer being
    told to choose a PALETTE item "informed by" a field that holds a FRAME value.
    The 2026-08-11 split made these two disjoint vocabularies, so reading the
    wrong one now yields a value that is not in the palette at all.
    """
    from teg_analysis.reporting.authoring import WRITER_VOICE
    palette_block = WRITER_VOICE[WRITER_VOICE.index("PALETTE —"):]
    palette_block = palette_block[:palette_block.index("\n\n\n")] if "\n\n\n" in palette_block else palette_block
    head = palette_block[:1200]
    assert "prominent_palette" in head
    # `prominent_vehicle` may appear, but only in the disambiguating warning.
    for m in __import__("re").finditer(r"prominent_vehicle", head):
        assert "NOT `prominent_vehicle`" in head[max(0, m.start() - 30):m.end() + 10], \
            "PALETTE block references prominent_vehicle outside the disambiguation note"


def test_prompts_never_reference_a_plan_field_that_does_not_exist():
    """Every "the plan's `x`" in a prompt must name a real schema field.

    This is the general form of issue 18. The `Literal` enums protect the
    *values* a field can hold; nothing protected the *field names* the prompts
    refer to in prose. Renaming `prominent_vehicle` left a prompt pointing at a
    field whose meaning had changed underneath it.

    Covers the nested models too (`RoundPlan.beat_ids`, `Payoff.seed`, …), since
    prompts legitimately reference those.
    """
    import re
    from teg_analysis.reporting import authoring, round_report
    from teg_analysis.reporting.story_plan import (
        StoryPlan, RoundPlan, Competition, PlayerArc, Payoff)

    known = set()
    for model in (StoryPlan, RoundPlan, Competition, PlayerArc, Payoff,
                  round_report.RoundStoryPlan, round_report.RoundCompetitionState,
                  round_report.RoundPlayerArc):
        known |= set(model.model_fields)

    prompts = {
        "WRITER_VOICE": authoring.WRITER_VOICE,
        "WRITER_FAITHFULNESS": authoring.WRITER_FAITHFULNESS,
        "DRY_DRAFT_SYSTEM_DETAILED": authoring.DRY_DRAFT_SYSTEM_DETAILED,
        "DRY_DRAFT_SYSTEM_LIGHT": authoring.DRY_DRAFT_SYSTEM_LIGHT,
        "ROUND_WRITER_SYSTEM": round_report.ROUND_WRITER_SYSTEM,
        "ROUND_DRY_DRAFT_SYSTEM": round_report.ROUND_DRY_DRAFT_SYSTEM,
    }
    pattern = re.compile(r"plan'?s?\s+\*{0,2}`([a-z_]+)`", re.IGNORECASE)

    dangling = [
        f"{name}: plan.{m.group(1)}"
        for name, prompt in prompts.items()
        for m in pattern.finditer(prompt)
        if m.group(1) not in known
    ]
    assert not dangling, (
        "prompt references a plan field that does not exist "
        f"(renamed or removed?): {dangling}")
