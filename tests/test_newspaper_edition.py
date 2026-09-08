"""Unit tests for `choose_arrangement` (newspaper edition layout rule).

Synthetic edition dicts only — no real artefact files, no network. See
`webapp/report_layout_prototypes/README.md` -> "Desktop composition" for the
E1/E2/E3 rule this pins.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from teg_analysis.reporting.newspaper_edition import choose_arrangement


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
