"""Tests for `teg_analysis.reporting.round_storyline` — the round-level
storyline-first pipeline.

The single most important property tested here is leak-safety: a mid-
tournament round report must not know what happened in later rounds of the
same TEG. See `round_storyline._assert_no_future_rounds` and the module
docstring for why.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.round_storyline import (
    RoundStorylinePlan,
    assemble_round_storyline_bundle,
    check_round_storyline_plan_consistency,
    round_draft_writer_system,
    round_storyline_system,
)


def _storyline(**kw):
    base = {"subject": "s", "why_it_matters": "w", "shape": "sh", "beat_ids": [],
            "compelling_score": 5, "humour_score": 5, "chosen_headline": "A Fine Round Indeed",
            "standfirst": "It happened.", "descriptor": "SIDEBAR"}
    base.update(kw)
    return base


def _plan(**kw):
    base = dict(
        title="t", title_candidates=["t"], theme="th", tone="house", opening_hook="oh",
        narrative_vehicles=["motif"], prominent_vehicle="motif", prominent_palette="records",
        is_final_round=False,
        round_story=_storyline(beat_ids=["r2_b01"]),
        race_story=_storyline(beat_ids=["r2_b02"]),
        discovered_storylines=[],
    )
    base.update(kw)
    return RoundStorylinePlan(**base)


# ---------------------------------------------------------------------------
# Leak safety — the central correctness property of this pipeline
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("teg,round_num", [(14, 2), (16, 2), (18, 3)])
def test_mid_tournament_bundle_carries_no_later_round(teg, round_num):
    bundle, _ = assemble_round_storyline_bundle(teg, round_num)
    assert bundle["is_final_round"] is False
    for b in bundle["beats"]:
        r = b.get("context", {}).get("round")
        if r is not None:
            assert r <= round_num
    for entry in bundle["course_context"].values():
        for course_entry in entry.values():
            assert course_entry["this_teg_best_round"] <= round_num


@pytest.mark.parametrize("teg,round_num", [(14, 4), (18, 4)])
def test_final_round_bundle_carries_tournament_outcome_keys(teg, round_num):
    bundle, _ = assemble_round_storyline_bundle(teg, round_num)
    assert bundle["is_final_round"] is True
    assert "win_anatomy" in bundle
    assert "win_counts" in bundle
    assert "double" in bundle


@pytest.mark.parametrize("teg,round_num", [(14, 1), (16, 2), (18, 3)])
def test_mid_tournament_bundle_omits_tournament_outcome_keys(teg, round_num):
    bundle, _ = assemble_round_storyline_bundle(teg, round_num)
    assert "win_anatomy" not in bundle
    assert "win_counts" not in bundle
    assert "double" not in bundle
    assert "tournament_shape" not in bundle


def test_bundle_carries_the_new_enrichment_keys():
    bundle, _ = assemble_round_storyline_bundle(16, 2)
    for key in ("round_ranks", "round_of_the_day", "race_movement", "course_context",
               "player_history"):
        assert key in bundle


def test_round_1_bundle_has_no_prior_state():
    bundle, _ = assemble_round_storyline_bundle(16, 1)
    assert bundle["race_movement"].get("is_round_1") is True
    assert bundle["competition_state_prior"] == []


# ---------------------------------------------------------------------------
# Prompts — DESCRIPTOR_RULE always in, DOUBLE_RULE only on the final round
# ---------------------------------------------------------------------------
def test_editor_prompt_always_carries_descriptor_rule():
    from teg_analysis.reporting import prompts
    assert prompts.DESCRIPTOR_RULE in round_storyline_system(False)
    assert prompts.DESCRIPTOR_RULE in round_storyline_system(True)


def test_double_rule_gated_on_final_round_for_both_prompts():
    from teg_analysis.reporting import prompts
    assert prompts.DOUBLE_RULE not in round_storyline_system(False)
    assert prompts.DOUBLE_RULE not in round_draft_writer_system(False)
    assert prompts.DOUBLE_RULE in round_storyline_system(True)
    assert prompts.DOUBLE_RULE in round_draft_writer_system(True)


def test_draft_writer_never_carries_descriptor_rule():
    from teg_analysis.reporting import prompts
    assert prompts.DESCRIPTOR_RULE not in round_draft_writer_system(False)
    assert prompts.DESCRIPTOR_RULE not in round_draft_writer_system(True)


def test_prompts_have_no_unfilled_placeholders():
    for prompt in (round_storyline_system(False), round_storyline_system(True),
                  round_draft_writer_system(False), round_draft_writer_system(True)):
        assert "{DOUBLE_RULE}" not in prompt
        assert "{VEHICLE_MENU}" not in prompt
        assert "{PALETTE_MENU}" not in prompt


# ---------------------------------------------------------------------------
# Schema round-trip
# ---------------------------------------------------------------------------
def test_plan_round_trips_through_model_dump():
    plan = _plan()
    dumped = plan.model_dump()
    reloaded = RoundStorylinePlan(**dumped)
    assert reloaded.round_story.subject == plan.round_story.subject


def test_is_final_round_true_requires_no_extra_fields():
    plan = _plan(is_final_round=True)
    assert plan.is_final_round is True


# ---------------------------------------------------------------------------
# Consistency checker
# ---------------------------------------------------------------------------
def _bundle(beats):
    return {"beats": beats, "is_final_round": False}


def test_unknown_beat_id_is_flagged():
    plan = _plan(round_story=_storyline(beat_ids=["ghost"]))
    warnings = check_round_storyline_plan_consistency(
        plan, _bundle([{"id": "r2_b01", "mandatory": False}]))
    assert any("unknown beat_ids" in w for w in warnings)


def test_missing_mandatory_beat_is_flagged():
    plan = _plan(round_story=_storyline(beat_ids=["r2_b01"]),
                race_story=_storyline(beat_ids=["r2_b01"]))
    bundle = _bundle([{"id": "r2_b01", "mandatory": False},
                      {"id": "cr01", "mandatory": True}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert any("mandatory beats not cited" in w for w in warnings)


def test_heavy_overlap_between_mandatory_storylines_is_flagged():
    plan = _plan(
        round_story=_storyline(beat_ids=["r2_b01", "r2_b02"]),
        race_story=_storyline(beat_ids=["r2_b01", "r2_b02"]),
    )
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert any("share" in w and "beat_ids" in w for w in warnings)


def test_thin_discovered_storyline_is_flagged():
    plan = _plan(discovered_storylines=[_storyline(beat_ids=["r2_b01"], compelling_score=4)])
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert any("thin" in w for w in warnings)


def test_clean_plan_has_no_warnings():
    plan = _plan(
        round_story=_storyline(beat_ids=["r2_b01"]),
        race_story=_storyline(beat_ids=["r2_b02"]),
    )
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert warnings == []


def test_is_final_round_mismatch_is_flagged():
    plan = _plan(is_final_round=True)
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    bundle["is_final_round"] = False
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert any("is_final_round" in w for w in warnings)


# ---------------------------------------------------------------------------
# round_by_round_status — the ground truth for cross-round streak/sweep claims.
# Regression coverage for the real TEG 3 R4 error: round_story claimed Jon
# Baker had "the best score in the field for the fourth round running", but
# round 2 was an exact tie with Henry Meller — not a win.
# ---------------------------------------------------------------------------
def test_round_by_round_status_flags_a_tie_as_not_a_clean_sweep():
    from teg_analysis.reporting.round_storyline import _round_by_round_status
    status = _round_by_round_status(3, 4)["trophy"]
    baker = status["Jon BAKER"]
    assert baker["statuses"] == ["best", "tied", "best", "best"]
    assert baker["best_or_tied_every_round"] is True
    assert baker["clean_sweep"] is False
    assert baker["tied_rounds"] == [2]


def test_round_by_round_status_is_bounded_to_round_num():
    from teg_analysis.reporting.round_storyline import _round_by_round_status
    status = _round_by_round_status(3, 2)["trophy"]
    assert status["Jon BAKER"]["rounds"] == [1, 2]


def test_streak_claim_in_subject_is_flagged():
    plan = _plan(round_story=_storyline(
        beat_ids=["r2_b01"],
        subject="the best score in the field for the fourth round running"))
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert any("streak/sweep" in w for w in warnings)


def test_no_streak_claim_is_silent():
    plan = _plan(round_story=_storyline(beat_ids=["r2_b01"], subject="a good round"))
    bundle = _bundle([{"id": "r2_b01", "mandatory": False}, {"id": "r2_b02", "mandatory": False}])
    warnings = check_round_storyline_plan_consistency(plan, bundle)
    assert not any("streak/sweep" in w for w in warnings)


# ---------------------------------------------------------------------------
# correct_streak_claim_in_plan — the plan-JSON half of the streak-claim fix.
# `apply_corrections` only edits report prose; `newspaper_edition._plan_headline`
# prefers the plan's `chosen_headline` over anything derived from the markdown,
# so a false streak claim baked into `chosen_headline` survives a prose-only
# correction untouched. Found correcting the real TEG 3 R4 output.
# ---------------------------------------------------------------------------
def test_correct_streak_claim_in_plan_rewrites_only_the_four_fields(tmp_path, monkeypatch):
    import json
    from unittest.mock import MagicMock
    from teg_analysis.reporting import round_storyline as rs_mod

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "commentary").mkdir(parents=True)
    plan = {
        "round_story": {
            "subject": "old false claim", "chosen_headline": "Old False Claim",
            "standfirst": "Old.", "why_it_matters": "Old reason.",
            "shape": "sh", "beat_ids": ["r4_b01"], "compelling_score": 7,
            "humour_score": 5, "descriptor": "SIDEBAR",
        },
    }
    path = tmp_path / "data" / "commentary" / "teg_9_round_4_storyline_plan.json"
    path.write_text(json.dumps(plan))

    fake_fields = rs_mod._StreakCorrectedFields(
        subject="new accurate claim", chosen_headline="New Accurate Claim",
        standfirst="New.", why_it_matters="New reason.")
    monkeypatch.setattr(rs_mod.llm, "generate_structured",
                        lambda *a, **k: (fake_fields, {}))

    result = rs_mod.correct_streak_claim_in_plan(9, 4, "round_story")
    assert result["chosen_headline"] == "New Accurate Claim"

    saved = json.loads(path.read_text())
    assert saved["round_story"]["chosen_headline"] == "New Accurate Claim"
    assert saved["round_story"]["subject"] == "new accurate claim"
    # Untouched fields survive exactly.
    assert saved["round_story"]["beat_ids"] == ["r4_b01"]
    assert saved["round_story"]["shape"] == "sh"
    assert saved["round_story"]["descriptor"] == "SIDEBAR"
