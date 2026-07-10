"""Unit tests for the final-round comeback/collapse functions in
teg_analysis/analysis/aggregation.py (T10 / REVIEW_PLAN.md Chat 8).

Uses a small hand-built two-player, one-TEG fixture with a known blown lead
after R3 and a known comeback in R4, for both GrossVP (lower-is-better) and
Stableford (higher-is-better).

Fixture story (GrossVP):
  - After R1-R3: A totals 0, B totals 15 -> A leads by 15.
  - R4 (3 holes): A shoots 3/3/3 (total 9); B shoots -2/-2/-3 (total -7).
  - Final: A = 9, B = 8 -> B overtakes A and wins; A's 15-shot lead is blown.
  - Hole-by-hole in R4: A leads through holes 1-2 (max lead 10 at hole 1),
    B takes over at hole 3.

Fixture story (Stableford): mirrored with higher-is-better direction so A
leads after R3 (36 vs 24) but B's big final round (19 pts) overtakes to win
43 vs 42.
"""

import pandas as pd
import pytest

from teg_analysis.analysis.aggregation import (
    calculate_final_round_differentials,
    calculate_biggest_leads_lost_after_r3,
    calculate_biggest_leads_lost_in_r4,
    calculate_biggest_comebacks,
)

TEG_NAME = "TEG 100"
TEG_NUM = 100


@pytest.fixture
def round_info_df():
    return pd.DataFrame({"TEGNum": [TEG_NUM] * 4, "Round": [1, 2, 3, 4]})


@pytest.fixture
def all_scores_df():
    rows = []

    # Rounds 1-3: one row per player/round carries the round total (Hole is
    # arbitrary since these functions only sum per Round).
    for player, gross, stableford in [("A", 0, 12), ("B", 5, 8)]:
        for rnd in (1, 2, 3):
            rows.append({
                "TEG": TEG_NAME, "TEGNum": TEG_NUM, "Player": player,
                "Round": rnd, "Hole": 1, "GrossVP": gross, "Stableford": stableford,
            })

    # Round 4 (final round), hole-by-hole so the in-round lead-tracking
    # function has evidence to walk through.
    r4_a = [(3, 2), (3, 2), (3, 2)]        # A: GrossVP total 9, Stableford total 6
    r4_b = [(-2, 6), (-2, 6), (-3, 7)]     # B: GrossVP total -7, Stableford total 19
    for hole, (g, s) in enumerate(r4_a, start=1):
        rows.append({
            "TEG": TEG_NAME, "TEGNum": TEG_NUM, "Player": "A",
            "Round": 4, "Hole": hole, "GrossVP": g, "Stableford": s,
        })
    for hole, (g, s) in enumerate(r4_b, start=1):
        rows.append({
            "TEG": TEG_NAME, "TEGNum": TEG_NUM, "Player": "B",
            "Round": 4, "Hole": hole, "GrossVP": g, "Stableford": s,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# calculate_final_round_differentials
# ---------------------------------------------------------------------------

def test_final_round_differentials_gross(all_scores_df, round_info_df):
    result = calculate_final_round_differentials(all_scores_df, round_info_df, measure="GrossVP")

    assert list(result["Player"]) == ["B", "A"]  # sorted ascending (best R4 score first)
    b_row = result[result["Player"] == "B"].iloc[0]
    a_row = result[result["Player"] == "A"].iloc[0]

    assert b_row["Final Round"] == 4
    assert b_row["Final Round Score"] == -7
    assert b_row["Rank After R3"] == 2  # B was behind after R3
    assert b_row["Total Score"] == 8
    assert b_row["Final Rank"] == 1

    assert a_row["Final Round Score"] == 9
    assert a_row["Rank After R3"] == 1  # A led after R3
    assert a_row["Total Score"] == 9
    assert a_row["Final Rank"] == 2


def test_final_round_differentials_stableford(all_scores_df, round_info_df):
    result = calculate_final_round_differentials(all_scores_df, round_info_df, measure="Stableford")

    assert list(result["Player"]) == ["B", "A"]  # sorted descending (best R4 score first)
    b_row = result[result["Player"] == "B"].iloc[0]
    a_row = result[result["Player"] == "A"].iloc[0]

    assert b_row["Final Round Score"] == 19
    assert b_row["Rank After R3"] == 2
    assert b_row["Total Score"] == 43
    assert b_row["Final Rank"] == 1

    assert a_row["Final Round Score"] == 6
    assert a_row["Rank After R3"] == 1
    assert a_row["Total Score"] == 42
    assert a_row["Final Rank"] == 2


# ---------------------------------------------------------------------------
# calculate_biggest_leads_lost_after_r3
# ---------------------------------------------------------------------------

def test_leads_lost_after_r3_gross(all_scores_df, round_info_df):
    result = calculate_biggest_leads_lost_after_r3(all_scores_df, round_info_df, measure="GrossVP")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["TEG"] == TEG_NAME
    assert row["Leader After R3"] == "A"
    assert row["Gap to 2nd"] == 15
    assert row["Winner"] == "B"
    assert row["Leader Final Position"] == 2


def test_leads_lost_after_r3_stableford(all_scores_df, round_info_df):
    result = calculate_biggest_leads_lost_after_r3(all_scores_df, round_info_df, measure="Stableford")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Leader After R3"] == "A"
    assert row["Gap to 2nd"] == 12
    assert row["Winner"] == "B"
    assert row["Leader Final Position"] == 2


# ---------------------------------------------------------------------------
# calculate_biggest_leads_lost_in_r4
# ---------------------------------------------------------------------------

def test_leads_lost_in_r4_gross(all_scores_df, round_info_df):
    result = calculate_biggest_leads_lost_in_r4(all_scores_df, round_info_df, measure="GrossVP")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Player"] == "A"
    assert row["Max Lead in R4"] == 10
    assert row["Hole of Max Lead"] == 1
    assert row["Winner"] == "B"
    assert row["Final Gap"] == 1


def test_leads_lost_in_r4_stableford(all_scores_df, round_info_df):
    result = calculate_biggest_leads_lost_in_r4(all_scores_df, round_info_df, measure="Stableford")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Player"] == "A"
    assert row["Max Lead in R4"] == 8
    assert row["Hole of Max Lead"] == 1
    assert row["Winner"] == "B"
    assert row["Final Gap"] == 1


# ---------------------------------------------------------------------------
# calculate_biggest_comebacks
# ---------------------------------------------------------------------------

def test_biggest_comebacks_gross(all_scores_df, round_info_df):
    result = calculate_biggest_comebacks(all_scores_df, round_info_df, measure="GrossVP")

    assert list(result["Player"]) == ["B", "A"]  # sorted by gap closed, descending
    b_row = result[result["Player"] == "B"].iloc[0]
    a_row = result[result["Player"] == "A"].iloc[0]

    assert b_row["Gap After R3"] == 15
    assert b_row["Player R4 Score"] == -7
    assert b_row["Leader R4 Score"] == -7
    assert b_row["Gap Closed"] == 15
    assert b_row["Final Position"] == 1
    assert b_row["Winner"] == "B"

    assert a_row["Gap After R3"] == 0
    assert a_row["Gap Closed"] == -1
    assert a_row["Final Position"] == 2


def test_biggest_comebacks_stableford(all_scores_df, round_info_df):
    result = calculate_biggest_comebacks(all_scores_df, round_info_df, measure="Stableford")

    assert list(result["Player"]) == ["B", "A"]
    b_row = result[result["Player"] == "B"].iloc[0]
    a_row = result[result["Player"] == "A"].iloc[0]

    assert b_row["Gap After R3"] == 12
    assert b_row["Player R4 Score"] == 19
    assert b_row["Leader R4 Score"] == 19
    assert b_row["Gap Closed"] == 12
    assert b_row["Final Position"] == 1

    assert a_row["Gap After R3"] == 0
    assert a_row["Gap Closed"] == -1
    assert a_row["Final Position"] == 2
