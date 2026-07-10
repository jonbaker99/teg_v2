"""Unit tests for the Batch-3 eclectic analysis additions:
teg_analysis.analysis.eclectic.eclectic_player_teg_totals, rank_teg_eclectics,
and calculate_eclectic_contributions.
"""
import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teg_analysis.analysis.eclectic import (
    eclectic_player_teg_totals,
    rank_teg_eclectics,
    calculate_eclectic_contributions,
)


def _row(player, pl, teg_num, round_, hole, grossvp):
    return {
        "Player": player, "Pl": pl, "TEGNum": teg_num, "Round": round_,
        "Hole": hole, "GrossVP": grossvp,
    }


@pytest.fixture
def teg2_data():
    """Two players, TEG 2, two rounds, three holes.

    Alice: R1 = [0, 1, 2], R2 = [1, -1, 2]  -> personal eclectic: [0, -1, 2] = 1
    Bob:   R1 = [1, 0, 1],  R2 = [2, 1, 0]  -> personal eclectic: [1, 0, 0] = 1

    Team eclectic per hole (min across both players/rounds):
      hole1: min(0,1,1,2) = 0 (Alice R1, solo)
      hole2: min(1,0,-1,1) = -1 (Alice R2, solo)
      hole3: min(2,1,2,0) = 0 (Bob R2, solo)
    Team eclectic total = -1.

    Alice's personal eclectic per hole: hole1=0, hole2=-1, hole3=2 -> matches
    team on hole1 and hole2 (both solo, since only Alice reaches those values).
    Bob's personal eclectic: hole1=1, hole2=0, hole3=0 -> matches team on
    hole3 only (solo).
    """
    rows = []
    rows.append(_row("Alice", "AL", 2, 1, 1, 0))
    rows.append(_row("Alice", "AL", 2, 1, 2, 1))
    rows.append(_row("Alice", "AL", 2, 1, 3, 2))
    rows.append(_row("Alice", "AL", 2, 2, 1, 1))
    rows.append(_row("Alice", "AL", 2, 2, 2, -1))
    rows.append(_row("Alice", "AL", 2, 2, 3, 2))

    rows.append(_row("Bob", "BO", 2, 1, 1, 1))
    rows.append(_row("Bob", "BO", 2, 1, 2, 0))
    rows.append(_row("Bob", "BO", 2, 1, 3, 1))
    rows.append(_row("Bob", "BO", 2, 2, 1, 2))
    rows.append(_row("Bob", "BO", 2, 2, 2, 1))
    rows.append(_row("Bob", "BO", 2, 2, 3, 0))
    return pd.DataFrame(rows)


@pytest.fixture
def multi_teg_data(teg2_data):
    """teg2_data plus a TEG 1 with the same players, engineered so Alice and
    Bob tie for the all-time #1 rank (Total = -5 each) and TEG 2 is what
    teg2_data computes (Total = -1, see teg2_data docstring)."""
    rows = teg2_data.to_dict("records")

    # TEG 1: single round, three holes, Alice and Bob each personal-eclectic
    # to a Total of -5 (tied for all-time best in the pool).
    rows.append(_row("Alice", "AL", 1, 1, 1, -2))
    rows.append(_row("Alice", "AL", 1, 1, 2, -2))
    rows.append(_row("Alice", "AL", 1, 1, 3, -1))

    rows.append(_row("Bob", "BO", 1, 1, 1, -2))
    rows.append(_row("Bob", "BO", 1, 1, 2, -2))
    rows.append(_row("Bob", "BO", 1, 1, 3, -1))

    return pd.DataFrame(rows)


def test_eclectic_player_teg_totals(teg2_data):
    totals = eclectic_player_teg_totals(teg2_data)
    totals = totals.set_index(["Player", "TEGNum"])["Total"]
    assert totals[("Alice", 2)] == 0 + -1 + 2  # 1
    assert totals[("Bob", 2)] == 1 + 0 + 0      # 1


def test_rank_teg_eclectics_tie_and_own_history(multi_teg_data):
    """TEG 1 has Alice and Bob tied at Total=-5 (both rank 1 in the all-time
    pool of 4 rows); TEG 2 totals are both 1 (rank 3, tied) in the same pool.
    Own-history: each player has 2 TEGs, so TEG1 (their better total) ranks 1
    of 2 and TEG2 ranks 2 of 2."""
    complete = {1, 2}

    ranks_1 = rank_teg_eclectics(multi_teg_data, teg_num=1, complete_teg_nums=complete)
    ranks_1 = ranks_1.set_index("Player")
    assert ranks_1.loc["Alice", "Total"] == -5
    assert ranks_1.loc["Bob", "Total"] == -5
    # Tied for best across the 4-row all-time pool (Alice T1, Alice T2, Bob T1, Bob T2).
    assert ranks_1.loc["Alice", "AllTimeRank"] == 1
    assert ranks_1.loc["Bob", "AllTimeRank"] == 1
    assert ranks_1.loc["Alice", "AllTimeN"] == 4
    assert ranks_1.loc["Alice", "OwnRank"] == 1
    assert ranks_1.loc["Alice", "OwnN"] == 2

    ranks_2 = rank_teg_eclectics(multi_teg_data, teg_num=2, complete_teg_nums=complete)
    ranks_2 = ranks_2.set_index("Player")
    assert ranks_2.loc["Alice", "Total"] == 1
    # TEG 2 total (1) is worse than TEG 1 (-5) for both players -> tied for
    # rank 3 in the all-time pool (both TEG-1 rows share rank 1).
    assert ranks_2.loc["Alice", "AllTimeRank"] == 3
    assert ranks_2.loc["Bob", "AllTimeRank"] == 3
    # Own-history: TEG 2 is each player's worse result -> rank 2 of 2.
    assert ranks_2.loc["Alice", "OwnRank"] == 2
    assert ranks_2.loc["Alice", "OwnN"] == 2


def test_rank_teg_eclectics_in_progress_pool_restriction(multi_teg_data):
    """If teg_num=2 is NOT in complete_teg_nums, the all-time pool still
    includes teg_num's own rows (per the plan: 'the current TEG's own total
    is always included for the player's own-history rank'), but excludes any
    other incomplete TEGs. Here TEG 1 is complete and TEG 2 is not."""
    complete = {1}  # TEG 2 excluded -> in-progress
    ranks_2 = rank_teg_eclectics(multi_teg_data, teg_num=2, complete_teg_nums=complete)
    ranks_2 = ranks_2.set_index("Player")
    # Pool = TEG 1 (2 rows, complete) + TEG 2's own rows (2 rows) = 4.
    assert ranks_2.loc["Alice", "AllTimeN"] == 4
    assert ranks_2.loc["Alice", "Total"] == 1


def test_calculate_eclectic_contributions(teg2_data):
    contrib = calculate_eclectic_contributions(teg2_data).set_index("Player")

    # Alice solo on holes 1 and 2 (team eclectic reached only by her).
    assert contrib.loc["Alice", "ecl_holes"] == 2
    assert contrib.loc["Alice", "ecl_solo"] == 2
    # Bob solo on hole 3 only.
    assert contrib.loc["Bob", "ecl_holes"] == 1
    assert contrib.loc["Bob", "ecl_solo"] == 1

    # Impact: hand-computed. Team eclectic total (with everyone) = -1.
    # Without Alice: team eclectic per hole would be Bob-only:
    #   hole1=1, hole2=0, hole3=0 -> total 1. Impact = -1 - 1 = -2.
    assert contrib.loc["Alice", "ecl_impact"] == -2
    # Without Bob: team eclectic would be Alice-only: hole1=0, hole2=-1,
    # hole3=2 -> total 1. Impact = -1 - 1 = -2.
    assert contrib.loc["Bob", "ecl_impact"] == -2

    # All impacts are <= 0.
    assert (contrib["ecl_impact"] <= 0).all()


def test_calculate_eclectic_contributions_empty():
    empty = pd.DataFrame(columns=["Pl", "Player", "Hole", "GrossVP"])
    result = calculate_eclectic_contributions(empty)
    assert result.empty
    assert list(result.columns) == ["Pl", "Player", "ecl_holes", "ecl_solo", "ecl_impact"]
