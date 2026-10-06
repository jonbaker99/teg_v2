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
