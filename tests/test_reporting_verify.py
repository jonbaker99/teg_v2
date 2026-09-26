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
    # usual anchor, is missing its report_final.md — known issue 14.) The legacy
    # chain was archived to `archive 2026 v3/` once /teg-reports stopped reading
    # it (2026-09-11); read from there rather than the (now storyline-first-only)
    # canonical path.
    text = open("data/commentary/archive 2026 v3/teg_17_report_final.md").read()
    findings = verify_report(17, text=text)
    assert all(isinstance(f, Finding) for f in findings)


def test_teg10_r3_arithmetic_error_is_fixed():
    """The published error was corrected; guard against reintroduction.

    Scoped to the arithmetic rule rather than asserting an empty findings list.
    The blanket version broke when `no_em_dashes` was added on 2026-08-15: every
    report generated before the em-dash ban trips it, which is the check working,
    not the arithmetic regressing. Same pattern as the TEG 5 beat-id guard below.
    """
    text = open("data/commentary/archive 2026 v3/teg_10_round_3_report_final.md").read()
    findings = verify_report(10, round_num=3, text=text)
    assert [f for f in findings if f.rule == "arithmetic_claims"] == []
    assert [f for f in findings if f.severity == "error"] == []


def test_teg5_beat_ids_are_stripped():
    """TEG 5 shipped 41 raw beat IDs to readers; they were removed."""
    text = open("data/commentary/archive 2026 v3/teg_5_report_final.md").read()
    assert [f for f in verify_report(5, text=text) if f.rule == "no_beat_ids"] == []


# ---------------------------------------------------------------------------
# WP1 — `--label` and the (now-live) storyline-first default
# ---------------------------------------------------------------------------
def test_all_glob_finds_the_storylinefirst_chain(tmp_path, monkeypatch):
    """`--all` used to glob `report_final.md`, which nothing writes any more —
    it silently matched zero files. This is the regression guard: the
    tournament pattern must match the tournament file only, not the round
    file that also ends `_report_storylinefirst.md`."""
    import glob
    import os
    import re

    from teg_analysis.reporting import paths, verify

    monkeypatch.setattr(paths, "get_variant", lambda: None)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "commentary").mkdir(parents=True)
    for name in ("teg_20_report_storylinefirst.md", "teg_20_round_1_report_storylinefirst.md",
                "teg_20_report_final.md"):
        (tmp_path / "data" / "commentary" / name).write_text("placeholder")

    tournament = [p for p in glob.glob(f"{paths.output_dir()}/teg_*_report_storylinefirst.md")
                 if re.match(r"teg_(\d+)_report_storylinefirst\.md$", os.path.basename(p))]
    assert len(tournament) == 1
    rounds = [p for p in glob.glob(f"{paths.output_dir()}/teg_*_round_*_report_storylinefirst.md")
             if re.match(r"teg_(\d+)_round_(\d+)_report_storylinefirst\.md$", os.path.basename(p))]
    assert len(rounds) == 1
    legacy = [p for p in glob.glob(f"{paths.output_dir()}/teg_*_report_final.md")
             if re.match(r"teg_(\d+)_report_final\.md$", os.path.basename(p))]
    assert len(legacy) == 1


def test_write_findings_round_trips(tmp_path, monkeypatch):
    from teg_analysis.reporting import paths, verify

    monkeypatch.setattr(paths, "get_variant", lambda: None)
    monkeypatch.chdir(tmp_path)
    findings = [Finding("no_em_dashes", "warning", "test", "excerpt", source="mechanical")]
    path = verify.write_findings(9, findings, label="storylinefirst")
    assert path.endswith("teg_9_verify.json")
    import json
    with open(path) as f:
        payload = json.load(f)
    assert payload["errors"] == 0 and payload["warnings"] == 1
    assert payload["findings"][0]["rule"] == "no_em_dashes"


# ---------------------------------------------------------------------------
# WP4 — claim checkers, hand-written fixtures against real TEG 18 data.
# No LLM call: claims are constructed directly and fed to `check_claim_list`.
# Acceptance (FACTCHECK_PLAN.md): items 1 and 4 are errors; 2 and 5 are
# warnings. Item 3 (a cross-sentence span-redundancy ambiguity) is not
# mechanically checkable from a single claim in this first cut — see the
# module docstring in `claims.py` for what IS covered.
# ---------------------------------------------------------------------------
class TestClaimChecks:
    """Grouped so `fb` (a real TEG 18 FactBase) is built once, not per test."""

    @pytest.fixture(scope="class")
    @classmethod
    def fb(cls):
        from teg_analysis.reporting.claims import build_fact_base
        return build_fact_base(18)

    def test_item1_hole_score_error(self, fb):
        from teg_analysis.reporting.claims import Claim, check_claim_list
        claims = [Claim(type="hole_score", quote="Jon Baker's six at the 7th",
                        player="Jon Baker", round=2, hole=7, score=6)]
        findings = check_claim_list(fb, claims)
        assert len(findings) == 1
        assert findings[0].severity == "error"
        assert findings[0].source == "claim"
        assert "8" in findings[0].detail

    def test_item4_comparison_warning(self, fb):
        from teg_analysis.reporting.claims import Claim, check_claim_list
        claims = [Claim(
            type="comparison",
            quote="Patterson was comfortably the better player over four rounds",
            players=["John Patterson", "Alex Baker"])]
        findings = check_claim_list(fb, claims)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_item2_weekday_mismatch_is_warning_not_error(self, fb):
        from teg_analysis.reporting.claims import Claim, check_claim_list
        # R2 is actually Sunday — an extractor attributing "Sunday" to R1
        # (the paragraph it appeared in) is the item-2 shape.
        claims = [Claim(type="weekday", quote="added another eight at the 4th on Sunday",
                        round=1, weekday="Sunday")]
        findings = check_claim_list(fb, claims)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_item5_shared_rank_is_warning(self, fb):
        from teg_analysis.reporting.claims import Claim, check_claim_list
        # Real TEG 18 shape: a technically-correct rank number that hides a
        # tie. Wooden Spoon claims use the ORDINARY Trophy rank column (1 =
        # best) — real prose always phrases spoon standings as ordinary field
        # position ("dropped to fourth"), never an inverted "spoon rank"
        # (2026-09-26: comparing against the inverted column produced 19
        # false errors in the full-corpus sweep). Ties are preserved either
        # way (a pure affine transform), so any tied hole works for this test.
        from teg_analysis.reporting.settled_facts import build_hole_timeline
        tl = build_hole_timeline(18)
        teg_df, rank_col = tl["teg_df"], tl["cols"]["rank_hole"]
        tied = None
        for (rnd, hole), g in teg_df.groupby(["Round", "Hole"]):
            dupes = g[g[rank_col].duplicated(keep=False)]
            if not dupes.empty:
                row = dupes.iloc[0]
                tied = (int(rnd), int(hole), row["Player"], int(row[rank_col]))
                break
        assert tied is not None, "expected at least one tied Trophy rank in TEG 18"
        rnd, hole, player, rank = tied
        claims = [Claim(type="rank_change", quote=f"{player} was in the Spoon race",
                        player=player, round=rnd, hole=hole,
                        competition="Wooden Spoon", value=rank)]
        findings = check_claim_list(fb, claims)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_quote_not_in_text_is_dropped_before_checking(self):
        from teg_analysis.reporting.claims import extract_claims
        # extract_claims itself needs an LLM call; test the filter directly
        # via the ClaimList construction it applies the same rule to.
        from teg_analysis.reporting.claims import Claim, ClaimList
        result = ClaimList(claims=[
            Claim(type="hole_score", quote="this text is not in the report",
                 player="X", round=1, hole=1, score=4),
        ])
        report_text = "Nothing here matches that quote at all."
        survivors = [c for c in result.claims if c.quote and c.quote in report_text]
        assert survivors == []

    def test_unchecked_claim_type_is_not_silently_dropped(self, fb):
        from teg_analysis.reporting.claims import Claim, check_claim_list
        claims = [Claim(type="record", quote="his best round at this course",
                        player="Jon Baker", competition="Some Course")]
        findings = check_claim_list(fb, claims)
        assert len(findings) == 1
        assert findings[0].severity == "unchecked"
