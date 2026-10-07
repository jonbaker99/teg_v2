"""`data/course_info.csv` sanity: pars match the hole data, ratings are sourced
and in the range WHS allows.

Ratings are men's Course Rating / Slope Rating from the tee TEG plays (yellow
or the club's equivalent). A blank rating is allowed (not found); a rating
without a source is not, for the same reason course colour needs sources.
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
CI = pd.read_csv(ROOT / "data" / "course_info.csv")
PAR_TOTALS = pd.read_csv(ROOT / "data" / "course_pars.csv").groupby("Course")["Par"].sum()
ROWS = [r for _, r in CI.iterrows()]


def test_rating_columns_exist():
    assert {"tee", "course_rating", "slope_rating", "rating_source"} <= set(CI.columns)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["Course"])
def test_par_matches_hole_data(row):
    if pd.notna(row["par"]) and row["Course"] in PAR_TOTALS:
        assert int(row["par"]) == int(PAR_TOTALS[row["Course"]])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["Course"])
def test_ratings_sourced_and_in_whs_range(row):
    cr, slope = row["course_rating"], row["slope_rating"]
    assert pd.isna(cr) == pd.isna(slope), "rating and slope come as a pair"
    if pd.isna(cr):
        return
    assert str(row["rating_source"]).startswith("http")
    assert pd.notna(row["tee"])
    assert 55 <= slope <= 155            # WHS slope range
    par = PAR_TOTALS.get(row["Course"])
    assert abs(cr - par) <= 6, f"course rating {cr} is implausible for par {par}"


# ---------------------------------------------------------------------------
# Interpreted difficulty (analysis/course_difficulty.py)
# ---------------------------------------------------------------------------
from teg_analysis.analysis import course_difficulty as cd

TABLE = pd.DataFrame({"Course": ["Easy", "Average", "Hard", "Unrated"],
                      "par": [72, 72, 72, 72], "course_rating": [70.0, 72.0, 74.0, None],
                      "slope_rating": [105, 113, 145, None]})


def test_average_course_is_zero_extra_strokes():
    assert cd.extra_strokes(72.0, 113, 72) == 0.0
    assert cd.band(0.0) == "standard"


def test_missing_figure_has_no_band():
    assert cd.band(None) is None and cd.band(float("nan")) is None


def test_bands_order_by_difficulty():
    bands = [cd.course_difficulty(c, TABLE)["band"] for c in ("Easy", "Average", "Hard")]
    assert bands == ["kind", "standard", "brutal"]


def test_unrated_course_has_no_difficulty():
    assert cd.course_difficulty("Unrated", TABLE) is None


def test_table_without_rating_columns_has_no_difficulty():
    # The live volume can hold a course_info.csv from before ratings existed.
    old = pd.DataFrame({"Course": ["Easy"], "par": [72]})
    assert cd.course_difficulty("Easy", old) is None


def test_rank_needs_enough_courses_and_respects_the_pool(monkeypatch):
    assert "rank_hardest" not in cd.course_difficulty("Hard", TABLE)
    monkeypatch.setattr(cd, "MIN_POOL_FOR_RANK", 2)
    assert cd.course_difficulty("Average", TABLE)["rank_hardest"] == 2
    # Leak-safety: ranked only against the courses passed in.
    assert cd.course_difficulty("Average", TABLE, among=["Easy"])["rank_hardest"] == 1


def test_every_rated_course_on_file_gets_a_band():
    for c in CI.loc[CI["slope_rating"].notna(), "Course"]:
        assert cd.course_difficulty(c, CI)["band"] in {"kind", "standard", "tough", "brutal"}
