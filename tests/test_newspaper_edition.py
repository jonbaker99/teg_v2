"""Unit tests for the newspaper edition's pure layout/parsing rules:
`choose_arrangement` and `split_value_qualifier`.

Synthetic edition dicts only — no real artefact files, no network. See
`webapp/report_layout_prototypes/README.md` -> "Desktop composition" for the
E1/E2/E3 rule this pins.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.newspaper_edition import (
    choose_arrangement,
    split_value_qualifier,
)


def _article(words: int, is_lead: bool = False, kicker: str = "SIDEBAR") -> dict:
    return {
        "words": words,
        "is_lead": is_lead,
        "kicker": "TROPHY" if is_lead else kicker,
        "compelling": 5,
        "humour": 5,
    }


def _edition(sub_words: list[int]) -> dict:
    articles = [_article(300, is_lead=True)] + [_article(w) for w in sub_words]
    return {"articles": articles}


def test_five_or_more_articles_is_e2():
    edition = _edition([250, 240, 230, 220])  # + lead = 5 articles
    assert choose_arrangement(edition) == "e2"


def test_three_subs_one_long_is_e3():
    # 430 / 273 / 250 -> longest is 1.64x the median of the other two.
    edition = _edition([430, 273, 250])
    assert choose_arrangement(edition) == "e3"


def test_three_subs_similar_length_is_e1():
    edition = _edition([260, 250, 240])
    assert choose_arrangement(edition) == "e1"


def test_two_subs_is_e1():
    edition = _edition([260, 240])
    assert choose_arrangement(edition) == "e1"



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
