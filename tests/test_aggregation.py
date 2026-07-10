"""Unit tests for teg_analysis.analysis.aggregation.aggregate_data.

Pins the fixed per-level group columns and deterministic column/row ordering
introduced when the dynamic `list_fields_by_aggregation_level` discovery was
replaced with the explicit `_AGGREGATION_LEVEL_FIELDS` map (finding T5).
"""
import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teg_analysis.analysis.aggregation import aggregate_data


@pytest.fixture
def fixture_data():
    """A tiny two-player, one-TEG, two-round, front/back-split frame.

    Carries every column that `aggregate_data` groups on so the fixed schema
    map is exercised without needing the real data files.
    """
    rows = []
    for pl, player, hc in [("AB", "Alice B", 10), ("CD", "Carol D", 18)]:
        for rnd, course, date in [(1, "Course X", "2020-01-01"), (2, "Course Y", "2020-01-02")]:
            for fb in ["Front", "Back"]:
                for hole in range(1, 10):
                    rows.append({
                        "Pl": pl, "Player": player,
                        "TEG": "TEG 1", "HC": hc, "TEGNum": 1, "Year": 2020, "Area": "UK",
                        "Round": rnd, "Date": date, "Course": course,
                        "TEG-Round": f"TEG 1|R{rnd}", "FrontBack": fb, "Hole": hole,
                        "Sc": 4, "GrossVP": 1, "NetVP": 0, "Stableford": 2,
                    })
    return pd.DataFrame(rows)


# The pinned group columns per level, coarsest level first (cumulative).
EXPECTED_GROUP_COLUMNS = {
    "Player": ["Pl", "Player"],
    "TEG": ["Pl", "Player", "TEG", "HC", "TEGNum", "Year", "Area"],
    "Round": ["Pl", "Player", "TEG", "HC", "TEGNum", "Year", "Area",
              "Round", "Date", "Course", "TEG-Round"],
    "FrontBack": ["Pl", "Player", "TEG", "HC", "TEGNum", "Year", "Area",
                  "Round", "Date", "Course", "TEG-Round", "FrontBack"],
}

MEASURES = ["Sc", "GrossVP", "NetVP", "Stableford"]


@pytest.mark.parametrize("level,expected_groups", EXPECTED_GROUP_COLUMNS.items())
def test_group_columns_are_pinned_per_level(fixture_data, level, expected_groups):
    """Column order is fixed and deterministic: group columns then measures."""
    result = aggregate_data(fixture_data, level)
    assert list(result.columns) == expected_groups + MEASURES


def test_default_measures(fixture_data):
    """Omitting measures uses the standard four in the documented order."""
    result = aggregate_data(fixture_data, "Player")
    assert list(result.columns) == ["Pl", "Player"] + MEASURES
    # Two players, each summed over 2 rounds * 18 holes = 36 holes.
    alice = result[result["Pl"] == "AB"].iloc[0]
    assert alice["Sc"] == 36 * 4
    assert alice["Stableford"] == 36 * 2


def test_measures_subset_preserves_order(fixture_data):
    result = aggregate_data(fixture_data, "TEG", measures=["GrossVP"])
    assert list(result.columns) == EXPECTED_GROUP_COLUMNS["TEG"] + ["GrossVP"]


def test_additional_group_fields_appended_deduped(fixture_data):
    """Extra group fields append in order; already-grouped ones don't duplicate."""
    result = aggregate_data(fixture_data, "TEG", additional_group_fields=["Course"])
    assert list(result.columns) == EXPECTED_GROUP_COLUMNS["TEG"] + ["Course"] + MEASURES

    # A field already in the level's group columns is not duplicated.
    result2 = aggregate_data(fixture_data, "TEG", additional_group_fields=["Area"])
    assert list(result2.columns) == EXPECTED_GROUP_COLUMNS["TEG"] + MEASURES


def test_additional_group_fields_accepts_string(fixture_data):
    result = aggregate_data(fixture_data, "TEG", additional_group_fields="Course")
    assert list(result.columns) == EXPECTED_GROUP_COLUMNS["TEG"] + ["Course"] + MEASURES


def test_invalid_level_raises(fixture_data):
    with pytest.raises(ValueError, match="Invalid aggregation level"):
        aggregate_data(fixture_data, "Nonsense")


def test_missing_columns_raises(fixture_data):
    with pytest.raises(ValueError, match="Missing columns"):
        aggregate_data(fixture_data.drop(columns=["Area"]), "TEG")


def test_rows_sorted_deterministically(fixture_data):
    """Row order is the group-column sort order, stable run to run."""
    result = aggregate_data(fixture_data, "Round").reset_index(drop=True)
    expected = result.sort_values(EXPECTED_GROUP_COLUMNS["Round"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(result, expected)
