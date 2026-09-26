"""Tests for readable streak-span wording in teg_analysis/analysis/streaks.py."""

from teg_analysis.analysis.streaks import describe_streak_span


def test_same_teg_and_round():
    assert (
        describe_streak_span("T17 R2 H9 to T17 R2 H10")
        == "TEG 17 R2, H9 to H10"
    )


def test_same_teg_different_rounds():
    assert (
        describe_streak_span("T07 R1 H8 to T07 R2 H12")
        == "TEG 7, R1 H8 to R2 H12"
    )


def test_different_tegs():
    assert (
        describe_streak_span("T10 R4 H1 to T11 R3 H5")
        == "TEG 10, R4 H1 to TEG 11, R3 H5"
    )


def test_current_streak_shows_start_to_date():
    assert (
        describe_streak_span("T02 R1 H1 to T02 R1 H5", is_current=True)
        == "TEG 2, R1 H1 to date"
    )


def test_unparseable_passthrough():
    assert describe_streak_span("-") == "-"
    assert describe_streak_span("not a location") == "not a location"
