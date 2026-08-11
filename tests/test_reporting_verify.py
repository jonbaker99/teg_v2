"""Tests for component D3 (`teg_analysis.reporting.verify`) and the schema
and era fixes that landed alongside it.

The anchor case for D3 is the TEG 10 R3 arithmetic error: a real, published
mistake written while the prompt rule forbidding it was already in place. If
`test_swing_claim_catches_teg10_r3_shape` ever goes green-by-accident (i.e. the
check stops firing on that shape), D3 has lost the thing it was built for.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.verify import (
    Finding,
    ReportContext,
    check_arithmetic_claims,
    check_no_beat_ids,
    check_no_invented_mechanisms,
    check_not_a_week,
    check_swing_claims,
    check_weekdays,
    format_findings,
    verify_report,
)


def _ctx(text: str, **kw) -> ReportContext:
    base = dict(teg_num=14, text=text, players=set(), venue={}, round_weekdays={})
    base.update(kw)
    return ReportContext(**base)


# ---------------------------------------------------------------------------
# The check that exists because of a real incident
# ---------------------------------------------------------------------------
def test_swing_claim_catches_teg10_r3_shape():
    """5 clear -> 11 adrift is a 16-point swing; the report said fourteen."""
    text = ("David Mullin began Round 3 five points clear in the Trophy and "
            "finished it eleven adrift in third. That is a fourteen-point swing "
            "on a day when nobody went round in a procession.")
    findings = check_swing_claims(_ctx(text))
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert "16-point swing" in findings[0].detail


def test_swing_claim_accepts_correct_arithmetic():
    text = ("He began five points clear and finished eleven adrift. "
            "That is a sixteen-point swing.")
    assert check_swing_claims(_ctx(text)) == []


def test_swing_claim_same_side_uses_difference():
    """Both endpoints ahead -> the swing is the difference, not the sum."""
    text = ("She began twelve points clear and finished four points clear. "
            "That is an eight-point swing.")
    assert check_swing_claims(_ctx(text)) == []


# ---------------------------------------------------------------------------
# Beat IDs
# ---------------------------------------------------------------------------
def test_beat_ids_flagged():
    findings = check_no_beat_ids(_ctx("He made a 10 at the par-5 16th (b25)."))
    assert [f.rule for f in findings] == ["no_beat_ids"]


def test_beat_ids_clean_text_passes():
    assert check_no_beat_ids(_ctx("He made a 10 at the par-5 16th.")) == []


def test_beat_id_check_does_not_flag_ordinary_words():
    """`b` followed by digits only — not every short token."""
    assert check_no_beat_ids(_ctx("The par-4 6th and the 18th were brutal.")) == []


# ---------------------------------------------------------------------------
# Invented mechanisms, with the negation carve-out
# ---------------------------------------------------------------------------
def test_countback_flagged_as_error():
    findings = check_no_invented_mechanisms(_ctx("He took it on countback."))
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_negated_countback_downgraded_to_warning():
    """'No countback was required' states the rule correctly — not a fabrication."""
    findings = check_no_invented_mechanisms(
        _ctx("Mullin's 10 outweighed Williams's 7. No countback was required."))
    assert len(findings) == 1
    assert findings[0].severity == "warning"


def test_playoff_variants_flagged():
    for phrase in ("a play-off", "a playoff", "sudden-death"):
        assert check_no_invented_mechanisms(_ctx(f"It went to {phrase}.")), phrase


# ---------------------------------------------------------------------------
# "A week"
# ---------------------------------------------------------------------------
def test_week_language_flagged():
    findings = check_not_a_week(_ctx("He led for the rest of the week."))
    assert [f.rule for f in findings] == ["not_a_week"]


def test_weekend_is_not_flagged_as_week():
    assert check_not_a_week(_ctx("A weekend of steady golf followed.")) == []


# ---------------------------------------------------------------------------
# Weekdays
# ---------------------------------------------------------------------------
def test_invented_weekday_flagged():
    ctx = _ctx("Bottom from Tuesday afternoon onwards.",
               round_weekdays={1: "Saturday", 2: "Sunday", 3: "Monday"})
    findings = check_weekdays(ctx)
    assert len(findings) == 1
    assert "Tuesday" in findings[0].detail


def test_real_weekday_passes():
    ctx = _ctx("The Sunday round at Boavista was the turning point.",
               round_weekdays={1: "Saturday", 2: "Sunday"})
    assert check_weekdays(ctx) == []


def test_weekday_check_noop_without_venue_data():
    assert check_weekdays(_ctx("On Tuesday he collapsed.")) == []


# ---------------------------------------------------------------------------
# Arithmetic sanity bounds
# ---------------------------------------------------------------------------
def test_impossible_over_par_total_flagged():
    findings = check_arithmetic_claims(_ctx("He was forty over par through three holes."))
    assert len(findings) == 1
    assert findings[0].severity == "warning"


def test_plausible_over_par_total_passes():
    assert check_arithmetic_claims(_ctx("He was six over par through three holes.")) == []


# ---------------------------------------------------------------------------
# Deterministic blocks are D2's output, not the writer's prose
# ---------------------------------------------------------------------------
def test_markdown_tables_are_not_checked():
    """Standings/records tables are code-generated; checking them flags D2."""
    text = "| Player | Note |\n|---|---|\n| A | the week |\n"
    assert check_not_a_week(_ctx(text)) == []


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def test_format_findings_reports_clean_pass():
    assert format_findings([], teg_num=9).startswith("✓ TEG 9")


def test_format_findings_counts_severities():
    out = format_findings([
        Finding("a", "error", "boom"),
        Finding("b", "warning", "hmm"),
    ], teg_num=9)
    assert "1 error(s), 1 warning(s)" in out


# ---------------------------------------------------------------------------
# End-to-end against the real library
# ---------------------------------------------------------------------------
def test_verify_report_runs_against_a_real_report():
    # TEG 17 is current-vintage and has a complete artefact chain. (TEG 14, the
    # usual anchor, is missing its report_final.md — known issue 14.)
    findings = verify_report(17)
    assert all(isinstance(f, Finding) for f in findings)


def test_teg10_r3_arithmetic_error_is_fixed():
    """The published error was corrected; guard against reintroduction."""
    assert verify_report(10, round_num=3) == []


def test_teg5_beat_ids_are_stripped():
    """TEG 5 shipped 41 raw beat IDs to readers; they were removed."""
    assert [f for f in verify_report(5) if f.rule == "no_beat_ids"] == []
