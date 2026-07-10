"""Unit tests for pure, LLM-free stages of teg_analysis/reporting (T10 /
REVIEW_PLAN.md Chat 8).

Covers only the deterministic pieces: event/beat scoring (reporting/events.py,
reporting/scoring.py) and markdown/CSS-class rendering (reporting/render.py).
No ANTHROPIC_API_KEY, no network, no data loading -- everything here is built
from minimal in-memory inputs. Nothing in reporting/llm.py is imported or
exercised.
"""

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
    assert result_label(grossvp=8, sc=12, par=4) == "+8 (blow-up)"


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
    assert ranked[0].total == 24.0
    assert ranked[1].total == 3.0


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


def test_build_at_a_glance_lists_winners_without_counts():
    plan = {"competitions": [
        {"name": "Trophy (Stableford)", "winner_or_loser": "Jon Baker"},
        {"name": "Green Jacket (Gross)", "winner_or_loser": "Dave Mullin"},
        {"name": "Wooden Spoon", "winner_or_loser": "Gregg Williams"},
    ]}
    out = render._build_at_a_glance(plan)
    assert '<section class="callout at-a-glance-box">' in out
    assert "Jon Baker" in out and "Dave Mullin" in out and "Gregg Williams" in out
    assert "(" not in out.split("Jon Baker")[1].split("</p>")[0]  # no ordinal suffix


def test_build_at_a_glance_annotates_with_win_counts():
    plan = {"competitions": [
        {"name": "Trophy (Stableford)", "winner_or_loser": "Jon Baker"},
    ]}
    win_counts = {"JON BAKER": {"trophy_wins": 2}}
    out = render._build_at_a_glance(plan, win_counts=win_counts)
    assert "(2nd Trophy)" in out


def test_apply_styling_inserts_dateline_and_callout_once():
    text = "# TEG 42 Report\n\nProse.\n"
    plan = {"competitions": [{"name": "Trophy (Stableford)", "winner_or_loser": "Jon Baker"}]}
    venue = {"teg_num": 42, "area": "Berkshire", "year": 2026}

    styled = render.apply_styling(text, plan, venue)
    assert styled.count("{.report-title}") == 1
    assert 'class="dateline"' in styled
    assert "TEG 42 | Berkshire | 2026" in styled
    assert 'at-a-glance-box' in styled

    # Idempotent: re-applying does not duplicate the callout/dateline.
    restyled = render.apply_styling(styled, plan, venue)
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
