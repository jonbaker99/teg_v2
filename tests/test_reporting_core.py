"""Unit tests for pure, LLM-free stages of teg_analysis/reporting (T10 /
REVIEW_PLAN.md Chat 8).

Covers only the deterministic pieces: event/beat scoring (reporting/events.py,
reporting/scoring.py) and markdown/CSS-class rendering (reporting/render.py).
No ANTHROPIC_API_KEY, no network, no data loading -- everything here is built
from minimal in-memory inputs. Nothing in reporting/llm.py is imported or
exercised.
"""

import pandas as pd
import pytest

from teg_analysis.reporting import scoring
from teg_analysis.reporting.events import (
    NotableEvent,
    result_label,
    hole_evidence,
    _ord,
    _proper,
    _maximal_runs,
    render_events_markdown,
)
from teg_analysis.reporting import render


# ---------------------------------------------------------------------------
# events.py: small pure helpers
# ---------------------------------------------------------------------------

def test_result_label_named_scores():
    assert result_label(grossvp=-2, sc=3, par=5) == "eagle"
    assert result_label(grossvp=-1, sc=3, par=4) == "birdie"
    assert result_label(grossvp=0, sc=4, par=4) == "par"
    assert result_label(grossvp=2, sc=6, par=4) == "double bogey"


def test_result_label_hole_in_one_overrides_grossvp_table():
    assert result_label(grossvp=-3, sc=1, par=4) == "hole-in-one"


def test_result_label_blowup_fallback():
    assert result_label(grossvp=8, sc=12, par=4) == "+8"


def test_hole_evidence_builds_expected_dict():
    row = {"PAR": 4, "Sc": 6, "GrossVP": 2, "Stableford": 0, "Hole": 7, "SI": 3}
    ev = hole_evidence(row)
    assert ev == {
        "hole": 7, "par": 4, "sc": 6, "grossvp": 2,
        "stableford": 0, "result": "double bogey", "si": 3,
    }


def test_hole_evidence_missing_si_is_omitted():
    row = {"PAR": 3, "Sc": 3, "GrossVP": 0, "Stableford": 2, "Hole": 5}
    ev = hole_evidence(row)
    assert "si" not in ev


def test_ord_suffixes():
    assert _ord(1) == "1st"
    assert _ord(2) == "2nd"
    assert _ord(3) == "3rd"
    assert _ord(4) == "4th"
    assert _ord(11) == "11th"
    assert _ord(12) == "12th"
    assert _ord(21) == "21st"


def test_proper_cases_all_caps_surname():
    assert _proper("John PATTERSON") == "John Patterson"


def test_maximal_runs_splits_on_gaps():
    rows = [1, 1, 0, 1, 1, 1, 0]
    runs = _maximal_runs(rows, lambda r: r == 1)
    assert runs == [[1, 1], [1, 1, 1]]


def test_maximal_runs_no_match_returns_empty():
    assert _maximal_runs([0, 0, 0], lambda r: r == 1) == []


# ---------------------------------------------------------------------------
# scoring.py: axis weighting / finalise ranking
# ---------------------------------------------------------------------------

def test_cap_clamps_to_band():
    assert scoring.cap(-5) == 0.0
    assert scoring.cap(15) == 10.0
    assert scoring.cap(5) == 5.0


def test_total_score_balanced_weights():
    ev = NotableEvent(teg_num=1, scope="hole", type="eagle", headline="x",
                      importance=3.0, rarity=4.0, entertainment=5.0)
    assert scoring.total_score(ev) == 12.0
    assert scoring.total_score(ev, weights=(2.0, 1.0, 0.0)) == 10.0


def test_finalise_ranks_events_descending_by_total():
    low = NotableEvent(teg_num=1, scope="hole", type="par", headline="low",
                       importance=1.0, rarity=1.0, entertainment=1.0)
    high = NotableEvent(teg_num=1, scope="hole", type="eagle", headline="high",
                        importance=8.0, rarity=8.0, entertainment=8.0)
    ranked = scoring.finalise([low, high], mode="balanced")

    assert [e.headline for e in ranked] == ["high", "low"]
    # Derived from the weights, not hardcoded — this asserted 24.0 (the old
    # 1.5+0.8+0.7) and broke on the 2026-08-14 re-profile for no real reason.
    # What is under test is that `total` is the weighted sum and the ordering
    # follows it, which holds at any setting.
    unit = sum(scoring.MODE_WEIGHTS["balanced"])
    assert ranked[0].total == pytest.approx(8.0 * unit)
    assert ranked[1].total == pytest.approx(1.0 * unit)


def test_finalise_fast_mode_leans_on_importance():
    imp_heavy = NotableEvent(teg_num=1, scope="hole", type="a", headline="imp",
                             importance=10.0, rarity=0.0, entertainment=0.0)
    ent_heavy = NotableEvent(teg_num=1, scope="hole", type="b", headline="ent",
                             importance=0.0, rarity=0.0, entertainment=10.0)
    ranked = scoring.finalise([ent_heavy, imp_heavy], mode="fast")
    assert [e.headline for e in ranked] == ["imp", "ent"]


def test_render_events_markdown_minimal():
    ev = NotableEvent(
        teg_num=42, scope="hole", type="eagle", round=2, course="Ashdown",
        headline="Jon eagles the par-5 14th (R2)",
        holes=[{"hole": 14, "par": 5, "sc": 3, "stableford": 4, "result": "eagle"}],
        importance=5.0, rarity=8.0, entertainment=7.0,
    )
    ev.total = 20.0
    md = render_events_markdown([ev], teg_num=42)

    assert "TEG 42" in md
    assert "Jon eagles the par-5 14th (R2)" in md
    assert "@ Ashdown" in md
    assert "H14(par 5) 3 = eagle, 4pt" in md


# ---------------------------------------------------------------------------
# render.py: CSS-class styling helpers (pure string transforms)
# ---------------------------------------------------------------------------

def test_add_report_title_class_tags_first_h1_only():
    text = "# TEG 42 Report\n\nSome prose.\n\n# Not the title\n"
    out = render._add_report_title_class(text)
    lines = out.splitlines()
    assert lines[0] == "# TEG 42 Report {.report-title}"
    assert "# Not the title" in out  # second H1 untouched


def test_add_report_title_class_is_idempotent():
    text = "# TEG 42 Report {.report-title}\n\nProse.\n"
    out = render._add_report_title_class(text)
    assert out.count("{.report-title}") == 1


def test_add_round_classes_tags_round_headings():
    text = "## Round 1: The Opener\n\nProse.\n\n## Round 2: The Comeback\n"
    out = render._add_round_classes(text)
    assert "## Round 1: The Opener {.round1 .round}" in out
    assert "## Round 2: The Comeback {.round2 .round}" in out


def test_add_round_classes_ignores_non_round_headings():
    text = "## Players\n"
    out = render._add_round_classes(text)
    assert out == text


def _tiny_all_data(rows):
    """Minimal `all_data`-shaped DataFrame for a single fake TEG: one row per
    player per hole, just the columns `get_teg_placings` needs."""
    return pd.DataFrame(rows)


def _fake_teg_df():
    # Three players, one row each, TEGNum 99 (post-Stableford era) — distinct
    # winners on each competition: Jon Baker (Trophy), Dave Mullin (Jacket),
    # Gregg Williams last on the Trophy metric (Spoon).
    return _tiny_all_data([
        {"TEGNum": 99, "Player": "Jon BAKER", "GrossVP": 4, "NetVP": -2, "Stableford": 40},
        {"TEGNum": 99, "Player": "Dave MULLIN", "GrossVP": 0, "NetVP": 0, "Stableford": 36},
        {"TEGNum": 99, "Player": "Gregg WILLIAMS", "GrossVP": 2, "NetVP": 2, "Stableford": 30},
    ])


def test_build_at_a_glance_lists_winners_without_counts():
    out = render._build_at_a_glance(99, df=_fake_teg_df())
    assert '<section class="callout at-a-glance-box">' in out
    assert "Jon Baker" in out and "Dave Mullin" in out and "Gregg Williams" in out
    assert "(" not in out.split("Jon Baker")[1].split("</p>")[0]  # no ordinal suffix


def test_build_at_a_glance_annotates_with_win_counts():
    win_counts = {"Jon BAKER": {"trophy_wins": 2}}
    out = render._build_at_a_glance(99, win_counts=win_counts, df=_fake_teg_df())
    assert "(2nd Trophy)" in out


def test_apply_styling_inserts_dateline_and_callout_once(monkeypatch):
    text = "# TEG 42 Report\n\nProse.\n"
    venue = {"teg_num": 42, "area": "Berkshire", "year": 2026}
    monkeypatch.setattr(
        render, "_build_at_a_glance",
        lambda teg_num, win_counts=None: '<section class="callout at-a-glance-box"></section>',
    )

    styled = render.apply_styling(text, 42, venue)
    assert styled.count("{.report-title}") == 1
    assert 'class="dateline"' in styled
    assert "TEG 42 | Berkshire | 2026" in styled
    assert 'at-a-glance-box' in styled

    # Idempotent: re-applying does not duplicate the callout/dateline.
    restyled = render.apply_styling(styled, 42, venue)
    assert restyled.count('class="dateline"') == 1
    assert restyled.count('at-a-glance-box') == 1


def test_inject_standings_per_round_inserts_before_next_heading():
    text = "# Title\n\n## Round 1: Opener\n\nProse.\n\n## Round 2: Closer\n\nMore prose.\n"
    standings = {
        1: '<p class="standings">R1 standings</p>',
        2: '<p class="standings">R2 standings</p>',
    }
    out = render._inject_standings(text, standings)
    assert out.index('R1 standings') < out.index("Round 2")
    assert 'R2 standings' in out


def test_inject_standings_appendix_when_no_round_headings():
    text = "# Title\n\nProse with no round headings.\n\n## Players\n\nCloser.\n"
    standings = {1: '<p class="standings">R1 standings</p>'}
    out = render._inject_standings(text, standings)
    assert "## Standings by round" in out
    assert out.index("Standings by round") < out.index("## Players")


def test_dedup_entries_combines_round_suffixes():
    entries = [
        "Baker posts a personal-best round: 44 pts (R2)",
        "Baker posts a personal-best round: 44 pts (R4)",
        "Someone else entirely",
    ]
    out = render._dedup_entries(entries)
    assert "Baker posts a personal-best round: 44 pts (R2, R4)" in out
    assert "Someone else entirely" in out
    assert len(out) == 2


def test_dedup_entries_sorts_round_suffixes_ascending():
    # Source events don't arrive in round order — the dedup must not just
    # concatenate them as found (regression: used to produce "(R4, R2)").
    entries = [
        "Baker posts a personal-best round: 44 pts (R4)",
        "Baker posts a personal-best round: 44 pts (R2)",
    ]
    out = render._dedup_entries(entries)
    assert out == ["Baker posts a personal-best round: 44 pts (R2, R4)"]


# ---------------------------------------------------------------------------
# render.py: Notable Achievements helpers
# ---------------------------------------------------------------------------

def test_a_or_an_before_vowel_sound_numbers():
    assert render._a_or_an(8) == "an"
    assert render._a_or_an(11) == "an"
    assert render._a_or_an(18) == "an"
    assert render._a_or_an(9) == "a"
    assert render._a_or_an(10) == "a"
    assert render._a_or_an(12) == "a"


def test_blowup_feat_numeric_score_not_word_label():
    ev = NotableEvent(
        teg_num=99, scope="hole", type="big_blowup", round=2,
        headline="Jon Baker runs up a 11 (sextuple bogey) at the 5th (R2)",
        players=["Jon Baker"],
        holes=[{"hole": 5, "par": 4, "sc": 11, "grossvp": 7, "result": "sextuple bogey"}],
        importance=5.0, rarity=5.0, entertainment=5.0,
    )
    out = render._blowup_feat(ev, is_pw=True, is_rw=False, show_round=True)
    assert "an 11 (+7)" in out
    assert "sextuple bogey" not in out
    assert "career-worst on a par-4" in out


def test_blowup_feat_merges_record_and_career_worst_tag():
    ev = NotableEvent(
        teg_num=99, scope="hole", type="big_blowup", round=1,
        headline="x", players=["Jon Baker"],
        holes=[{"hole": 5, "par": 4, "sc": 12, "grossvp": 8, "result": "+8"}],
        importance=5.0, rarity=5.0, entertainment=5.0,
    )
    out = render._blowup_feat(ev, is_pw=True, is_rw=True, show_round=False)
    assert out.count("par-4") == 1
    assert "a new TEG-record and career-worst on a par-4" in out


def test_get_teg_placings_applies_override(monkeypatch):
    from teg_analysis.analysis import history

    df = pd.DataFrame([
        {"TEGNum": 5, "Player": "David MULLIN", "GrossVP": 72, "NetVP": 12, "Stableford": 136},
        {"TEGNum": 5, "Player": "Stuart NEUMANN", "GrossVP": 88, "NetVP": 8, "Stableford": 139},
        {"TEGNum": 5, "Player": "Gregg WILLIAMS", "GrossVP": 126, "NetVP": -6, "Stableford": 153},
    ])
    monkeypatch.setattr(history, "TEG_OVERRIDES", {"TEG 5": {"Best Gross": "Stuart NEUMANN*"}})
    placings = history.get_teg_placings(df, 5)
    # Raw data favours David Mullin (72 < 88); the override promotes Neumann.
    assert placings["jacket"][0] == "Stuart NEUMANN"
    assert placings["jacket"][1] == "David MULLIN"


def test_get_teg_placings_no_override_sorts_by_score(monkeypatch):
    from teg_analysis.analysis import history

    df = pd.DataFrame([
        {"TEGNum": 6, "Player": "Jon BAKER", "GrossVP": 4, "NetVP": -2, "Stableford": 40},
        {"TEGNum": 6, "Player": "Dave MULLIN", "GrossVP": 0, "NetVP": 0, "Stableford": 36},
    ])
    monkeypatch.setattr(history, "TEG_OVERRIDES", {})
    placings = history.get_teg_placings(df, 6)
    assert placings["trophy"] == ["Jon BAKER", "Dave MULLIN"]
    assert placings["jacket"] == ["Dave MULLIN", "Jon BAKER"]
