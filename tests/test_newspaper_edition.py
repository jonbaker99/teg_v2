"""Unit tests for the newspaper edition's pure layout/parsing rules:
`plan_rows` and `split_value_qualifier`.

Synthetic edition dicts only — no real artefact files, no network. See
`plan_rows`'s docstring (teg_analysis/reporting/newspaper_edition.py) for the
row-packing rule this pins.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.newspaper_edition import (
    _degraded_storyline,
    _resolve_section,
    _round_only,
    _totals_only,
    plan_rows,
    split_value_qualifier,
)


def _article(words: int, kicker: str = "SIDEBAR") -> dict:
    return {
        "words": words,
        "is_lead": False,
        "kicker": kicker,
        "compelling": 5,
        "humour": 5,
    }


def _row_sizes(subs: list[dict]) -> list[int]:
    return [len(row) for row in plan_rows(subs)]


def test_two_remaining_subs_pack_as_promoted_plus_one_row():
    # 3 total subs (one promoted) -> remainder 2 -> [1],[2]
    subs = [_article(100, "GREEN JACKET"), _article(90), _article(80)]
    assert _row_sizes(subs) == [1, 2]


def test_three_remaining_subs_pack_as_promoted_plus_one_row():
    # 4 total subs -> remainder 3 -> [1],[3]
    subs = [_article(100, "GREEN JACKET"), _article(90), _article(80), _article(70)]
    assert _row_sizes(subs) == [1, 3]


def test_four_remaining_subs_split_into_two_rows_of_two():
    # 5 total subs -> remainder 4 -> [1],[2,2] not [1],[3,1]
    subs = [_article(100, "GREEN JACKET"), _article(90), _article(80),
            _article(70), _article(60)]
    assert _row_sizes(subs) == [1, 2, 2]


def test_six_remaining_subs_split_into_two_rows_of_three():
    # 7 total subs -> remainder 6 -> [1],[3,3]
    subs = [_article(100, "GREEN JACKET")] + [_article(90 - i) for i in range(6)]
    assert _row_sizes(subs) == [1, 3, 3]


def test_no_subs_produces_no_rows():
    assert plan_rows([]) == []


def test_one_sub_with_no_pair_is_a_lone_row():
    # No promotable "second lead" case doesn't arise once there's at least one
    # sub (_choose_second_story always returns something) — with exactly one
    # sub, that sub IS the promoted row and there is no remainder.
    subs = [_article(50)]
    assert _row_sizes(subs) == [1]


def test_rows_are_sorted_by_word_count_within_the_packed_rows():
    subs = [_article(100, "GREEN JACKET"), _article(50), _article(90), _article(70)]
    rows = plan_rows(subs)
    assert [a["words"] for a in rows[1]] == [90, 70, 50]


# ---------------------------------------------------------------------------
# _totals_only / _round_only — the appendix's two standings tables.
# ---------------------------------------------------------------------------


def test_totals_only_strips_the_round_score_bracket():
    row = "SN 156 (R4: 43) | DM 148 (R4: 38)"
    assert _totals_only(row) == "SN 156 | DM 148"


def test_round_only_swaps_in_the_bracketed_round_score():
    row = "SN 156 (R4: 43) | DM 148 (R4: 38)"
    assert _round_only(row) == "SN 43 | DM 38"


def test_round_only_passes_round_one_rows_through_unchanged():
    # Round 1 has no bracket — cumulative already equals the round score.
    row = "JP 39 | JB 38 | DM 33"
    assert _round_only(row) == row


def test_round_only_handles_signed_scores():
    row = "GW +37 (R2: +17) | JB +34 (R2: +14)"
    assert _round_only(row) == "GW +17 | JB +14"



# ---------------------------------------------------------------------------
# split_value_qualifier — the at-a-glance value carries two shapes in real
# data, and a parenthesis-only split would silently no-op on TEG 18's.
# ---------------------------------------------------------------------------


def test_parenthetical_qualifier_is_split_off():
    # TEG 14/16 shape.
    assert split_value_qualifier("David Mullin (3rd Trophy)") == (
        "David Mullin",
        "(3rd Trophy)",
    )


def test_em_dash_qualifier_is_split_off():
    # TEG 18 shape — long, and no parentheses at all.
    assert split_value_qualifier(
        "Alex Baker — 169 pts, by 8 from John Patterson"
    ) == ("Alex Baker", "— 169 pts, by 8 from John Patterson")


def test_value_with_no_qualifier_is_left_whole():
    assert split_value_qualifier("Just A Name") == ("Just A Name", "")


def test_parentheses_not_at_the_end_do_not_split():
    assert split_value_qualifier("Player (Jr) wins the day") == (
        "Player (Jr) wins the day",
        "",
    )


def test_only_the_final_parenthetical_splits():
    """Regression: a greedy `.*` matched from the FIRST "(" to the last ")",
    splitting at "(Jr)" and swallowing "wins" into the qualifier."""
    assert split_value_qualifier("Player (Jr) wins (1st Trophy)") == (
        "Player (Jr) wins",
        "(1st Trophy)",
    )


def test_earliest_separator_wins():
    """A dash before a trailing parenthetical splits at the dash."""
    assert split_value_qualifier("Alex Baker — 169 pts (a record)") == (
        "Alex Baker",
        "— 169 pts (a record)",
    )


# ---------------------------------------------------------------------------
# Section -> storyline matching. The anchor is the key; the heading is only a
# fallback, because heading text has broken this join twice (see the matcher's
# comment in `newspaper_edition.py`).
# ---------------------------------------------------------------------------
def _plan() -> dict:
    def sl(subject: str) -> dict:
        return {"subject": subject, "chosen_headline": "H", "standfirst": "S",
                "compelling_score": 5, "humour_score": 5}
    return {"trophy_storyline": sl("Trophy subject"),
            "jacket_storyline": sl("Jacket subject"),
            "spoon_storyline": sl("Spoon subject"),
            "discovered_storylines": [sl("First discovered"), sl("Second discovered")]}


def test_anchor_resolves_regardless_of_heading_text():
    """The whole point: a heading that matches no plan subject still resolves."""
    plan = _plan()
    matches = _resolve_section("A heading nobody planned",
                               "<!-- storyline: d1 -->\n\nProse.", plan)
    assert matches == [("SIDEBAR", plan["discovered_storylines"][1])]


def test_anchor_handles_a_merged_section():
    plan = _plan()
    matches = _resolve_section("Anything at all",
                               "<!-- storyline: d0,spoon -->\n\nProse.", plan)
    assert [k for k, _ in matches] == ["SIDEBAR", "WOODEN SPOON"]


def test_exact_subject_still_matches_when_there_is_no_anchor():
    """Reports written before anchors existed must keep working unchanged."""
    plan = _plan()
    assert _resolve_section("Trophy subject", "Prose.", plan) == [
        ("TROPHY", plan["trophy_storyline"])]


def test_unresolvable_section_degrades_instead_of_raising():
    """A preview that renders one section plainly beats a preview that 500s."""
    plan = _plan()
    matches = _resolve_section("Matches nothing", "No anchor here.", plan)
    assert matches == [_degraded_storyline("Matches nothing")]
    assert matches[0][1]["compelling_score"] == 0  # never promoted to lead


def test_an_anchor_past_the_end_of_the_plan_degrades():
    """A regenerated plan can be shorter than the report's anchors expect."""
    plan = _plan()
    matches = _resolve_section("Matches nothing", "<!-- storyline: d9 -->", plan)
    assert matches == [_degraded_storyline("Matches nothing")]


# ---------------------------------------------------------------------------
# ArticleFilter — which stories make the paper. Presentation only: nothing on
# disk changes, and a dropped story returns by moving a threshold.
# ---------------------------------------------------------------------------
def _scored(compelling, humour, is_lead=False, kicker="SIDEBAR"):
    return {"headline": "x", "compelling": compelling, "humour": humour,
            "is_lead": is_lead, "kicker": kicker}


def test_default_filter_prints_everything():
    """The default must be a no-op, or adding the filter silently changed reports."""
    from teg_analysis.reporting.newspaper_edition import KEEP_EVERYTHING, filter_articles

    articles = [_scored(0, 0), _scored(3, 1), _scored(10, 10)]
    kept, dropped = filter_articles(articles, KEEP_EVERYTHING)
    assert len(kept) == 3 and dropped == []


def test_match_all_requires_both_floors_and_any_requires_either():
    from teg_analysis.reporting.newspaper_edition import ArticleFilter, filter_articles

    articles = [_scored(9, 2), _scored(2, 9), _scored(9, 9)]

    kept, _ = filter_articles(articles, ArticleFilter(8, 8, match="all"))
    assert [(a["compelling"], a["humour"]) for a in kept] == [(9, 9)]

    kept, _ = filter_articles(articles, ArticleFilter(8, 8, match="any"))
    assert [(a["compelling"], a["humour"]) for a in kept] == [(9, 2), (2, 9), (9, 9)]


def test_min_combined_rescues_a_lopsided_scored():
    """A very funny but less compelling piece should survive a compelling floor."""
    from teg_analysis.reporting.newspaper_edition import ArticleFilter, filter_articles

    lopsided = _scored(5, 9)
    kept, dropped = filter_articles([lopsided], ArticleFilter(min_compelling=7))
    assert dropped == [lopsided]

    kept, dropped = filter_articles([lopsided], ArticleFilter(min_compelling=7, min_combined=13))
    assert kept == [lopsided] and dropped == []


def test_the_three_competitions_are_never_dropped():
    """A report that never says who won the Jacket has a hole in it, however dull
    that week's Jacket was. Only discovered (SIDEBAR) stories are filterable."""
    from teg_analysis.reporting.newspaper_edition import ArticleFilter, filter_articles

    trophy = _scored(1, 1, is_lead=True, kicker="TROPHY")
    jacket = _scored(1, 1, kicker="GREEN JACKET")
    spoon = _scored(1, 1, kicker="WOODEN SPOON")
    sidebar = _scored(1, 1, kicker="SIDEBAR")

    kept, dropped = filter_articles([trophy, jacket, spoon, sidebar],
                                    ArticleFilter(10, 10))
    assert kept == [trophy, jacket, spoon]
    assert dropped == [sidebar]


def test_a_merged_article_carrying_a_competition_is_kept():
    """Cross-cut sections join kickers with ' & '; one carrying a competition is
    still mandatory, so the test is substring not equality."""
    from teg_analysis.reporting.newspaper_edition import ArticleFilter, filter_articles

    merged = _scored(1, 1, kicker="WOODEN SPOON & SIDEBAR")
    kept, dropped = filter_articles([merged], ArticleFilter(10, 10))
    assert kept == [merged] and dropped == []


def test_dropped_articles_never_reach_the_page():
    """Otherwise every page carries the text of stories deliberately not shown."""
    from teg_analysis.reporting.newspaper_edition import for_page

    edition = {"teg": 14, "articles": [], "dropped_articles": [_scored(1, 1)]}
    assert "dropped_articles" not in for_page(edition)
    assert for_page(edition)["teg"] == 14
