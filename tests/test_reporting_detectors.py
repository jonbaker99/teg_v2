"""Tests for the WP2 detector fixes (FACTCHECK_PLAN.md) in `events.py` and
`course_history.py`. Real TEG 18 data throughout — these are the exact shapes
the fact-check diagnosis found, not synthetic fixtures.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting.course_history import detect_course_records


@pytest.fixture(scope="module")
def teg18_events():
    return build_notable_events(18)


# ---------------------------------------------------------------------------
# long_lead_lost — both players' hole evidence, item 1
# ---------------------------------------------------------------------------
def test_long_lead_lost_carries_both_players_hole_evidence(teg18_events):
    losses = [e for e in teg18_events if e.type == "long_lead_lost"]
    assert losses, "expected at least one long_lead_lost beat in TEG 18"
    for e in losses:
        players_in_holes = {h.get("player") for h in e.holes}
        assert set(e.players) <= players_in_holes | {None}
        assert len(e.holes) == 2, "expected evidence for both the previous and new leader"
        assert e.context["taken_at_hole"] == e.context["lost_at_hole"]


# ---------------------------------------------------------------------------
# Recaptures from a tie — the exact TEG 18 R2 Jacket shape (item 1)
# ---------------------------------------------------------------------------
def test_jacket_lead_recaptures_from_a_tie_are_detected(teg18_events):
    jacket_r2 = [
        e for e in teg18_events
        if e.type == "lead_change" and e.context.get("competition", "").startswith("Green")
        and e.round == 2
    ]
    holes = sorted(e.holes[0]["hole"] for e in jacket_r2 if e.holes)
    # FACTCHECK_PLAN.md: "The lead changed hands at R2 H6/7/9/10/12/13/14" —
    # before the fix, H7/H12/H14 (recaptures from a tie) fired nothing.
    assert holes == [6, 7, 9, 10, 12, 13, 14]
    outright_holes = {e.holes[0]["hole"] for e in jacket_r2
                      if e.holes and e.context.get("lead_type") == "outright"}
    assert {7, 9, 12, 14} <= outright_holes


def test_jacket_lead_change_uses_gross_ranks_not_trophy_ranks(teg18_events):
    """Adjacent bug found while fixing item 1: a Jacket lead_change beat used
    to report the Trophy's Stableford/NetVP rank in `rank_after`, not the
    Gross rank — so a "takes the lead" beat could show `rank_after` far from 1."""
    jacket = [e for e in teg18_events if e.type == "lead_change"
             and e.context.get("competition", "").startswith("Green")]
    assert jacket
    for e in jacket:
        assert e.context["rank_after"] == 1


# ---------------------------------------------------------------------------
# Spoon direction — item 5
# ---------------------------------------------------------------------------
def test_spoon_change_uses_spoon_direction_ranks(teg18_events):
    spoon = [e for e in teg18_events if e.type == "spoon_change"]
    assert spoon
    for e in spoon:
        assert "spoon_rank_after" in e.context
        assert "rank_before" not in e.context and "rank_after" not in e.context
        # Spoon rank 1 = worst; the beat fires on DROPPING to the bottom, so
        # spoon_rank_after must be 1 (a Trophy-direction rank_after would
        # instead show whatever the player's Trophy standing was — a
        # different, wrong-direction number).
        assert e.context["spoon_rank_after"] == 1
        assert "position_label" in e.context


def test_spoon_change_reports_ties(teg18_events):
    spoon = [e for e in teg18_events if e.type == "spoon_change"]
    tied = [e for e in spoon if e.context.get("tie_size", 1) > 1]
    assert tied, "expected at least one tied drop to the bottom in TEG 18"
    for e in tied:
        assert "tied_with" in e.context
        assert e.context["position_label"].startswith("T")


# ---------------------------------------------------------------------------
# tied_with / tie_size on lead_change
# ---------------------------------------------------------------------------
def test_lead_change_level_beats_carry_tied_with(teg18_events):
    level = [e for e in teg18_events if e.type == "lead_change"
            and e.context.get("lead_type") == "level"]
    assert level
    for e in level:
        assert e.context["tie_size"] > 1
        assert e.context["tied_with"], "a level (tied) lead_change must name who it's tied with"
        assert e.players[0] not in e.context["tied_with"]


# ---------------------------------------------------------------------------
# Course records — item 6, and the strict-inequality gap
# ---------------------------------------------------------------------------
def test_course_record_equalled_is_detected_within_the_same_teg():
    """FACTCHECK_PLAN.md item 6: Williams's R4 84 at the Stadium course
    equals Mullin's R3 84 of the SAME TEG. The old strict `<`/`>` logic only
    ever compared against TEGs before this one, so a same-TEG tie (or a
    same-TEG round beating an earlier same-TEG round) was invisible."""
    events = detect_course_records(18)
    equalled = [e for e in events if e["type"] == "course_record_equalled"]
    assert any(e["round"] == 4 and e["gross"] == 84 for e in equalled), (
        "expected an R4 84 to equal a same-TEG (or earlier) course record")


def test_course_records_include_every_type():
    events = detect_course_records(18)
    types = {e["type"] for e in events}
    # Not asserting every type fires for TEG 18 specifically (that depends on
    # what actually happened), just that the vocabulary produced is one of
    # the four documented types.
    assert types <= {"course_record_low", "course_record_high",
                     "course_record_equalled", "course_record_high_equalled"}


def test_course_record_equalled_names_the_record_holder():
    """TEG 18 R4: Williams's 84 equals the 84 Mullin shot in R3 of the same TEG."""
    eq = [e for e in detect_course_records(18) if e["type"] == "course_record_equalled"]
    assert eq[0]["record_holders"] == [{"player": "David Mullin", "teg": 18, "round": 3}]


def test_records_appendix_lists_course_records():
    """The appendix had no course-record line; WP6's sweep found 25 such facts
    missing from the prose. Round reports list only their own round's."""
    from teg_analysis.reporting.render import build_records_block

    block = build_records_block(18)
    assert "Course records:" in block
    assert ("Gregg Williams's 84 at PGA Catalunya - Stadium (R4) — equals the "
            "course record, set by David Mullin in R3") in block
    r4 = build_records_block(18, round_num=4)
    assert "Gregg Williams's 84 at PGA Catalunya - Stadium — equals" in r4
    assert "David Mullin's 84" not in r4


def test_course_record_goes_to_the_best_card_in_the_round():
    """TEG 11 R1: Mullin's 92 and Jon Baker's 90 both beat the Stadium's 94.
    Only Baker's 90 set the record; row order used to credit Mullin too."""
    lows = [(e["player"], e["gross"]) for e in detect_course_records(11)
            if e["type"] == "course_record_low" and e["course"] == "PGA Catalunya - Stadium"]
    assert lows == [("Jon Baker", 90)]
