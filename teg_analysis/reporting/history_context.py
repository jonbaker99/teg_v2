"""Cross-TEG player history for bundle enrichment.

`build_player_cross_teg_history(teg_num)` computes each player's wins,
finishing positions, and notable milestone strings across all *prior* TEGs
(TEGNums < teg_num). The milestones are pre-computed factual phrases the LLM
can use verbatim — "2nd Jacket", "back-to-back Spoons", "bridesmaid again" —
so they're grounded rather than invented.

Also exports `build_win_counts(teg_num)` for the deterministic at-a-glance
annotation in render.py, which needs only win tallies for the current TEG's
winners (called after the TEG is complete, so all TEGs ≤ teg_num are included).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _compute_teg_finishes(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-player per-TEG Trophy and Jacket finishing ranks.

    Uses the same era-aware Trophy metric as the rest of the pipeline.
    """
    from teg_analysis.analysis.scoring import get_net_competition_measure

    grouped = df.groupby(["TEGNum", "Player"]).agg(
        GrossVP=("GrossVP", "sum"),
        NetVP=("NetVP", "sum"),
        Stableford=("Stableford", "sum"),
    ).reset_index()

    rows = []
    for teg_num in sorted(grouped["TEGNum"].unique()):
        teg_data = grouped[grouped["TEGNum"] == teg_num].copy()
        net_measure = get_net_competition_measure(int(teg_num))

        if net_measure == "NetVP":
            teg_data = teg_data.sort_values("NetVP", ascending=True)
        else:
            teg_data = teg_data.sort_values("Stableford", ascending=False)
        teg_data["trophy_rank"] = range(1, len(teg_data) + 1)

        jacket = teg_data.sort_values("GrossVP", ascending=True)
        jacket = jacket.copy()
        jacket["jacket_rank"] = range(1, len(jacket) + 1)
        rank_map = dict(zip(jacket["Player"], jacket["jacket_rank"]))
        teg_data["jacket_rank"] = teg_data["Player"].map(rank_map)

        n_players = len(teg_data)
        for _, r in teg_data.iterrows():
            rows.append({
                "TEGNum": int(teg_num),
                "Player": r["Player"],
                "trophy_rank": int(r["trophy_rank"]),
                "jacket_rank": int(r["jacket_rank"]),
                "n_players": n_players,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["TEGNum", "Player", "trophy_rank", "jacket_rank", "n_players"]
    )


def _milestones(player: str, wins: dict, last_finishes: list[dict]) -> list[str]:
    """Generate pre-computed factual milestone strings for one player."""
    ms = []
    tw = wins["trophy_wins"]
    jw = wins["jacket_wins"]
    sp = wins["spoon_count"]

    # --- Win-count context strings (always included if positive) ---
    if tw > 0:
        ms.append(f"{tw} prior Trophy win{'s' if tw != 1 else ''}")
    if jw > 0:
        ms.append(f"{jw} prior Jacket win{'s' if jw != 1 else ''}")
    if sp > 0:
        ms.append(f"{sp} prior Wooden Spoon{'s' if sp != 1 else ''}")

    # --- Back-to-back streaks ---
    if len(last_finishes) >= 2:
        recent2 = last_finishes[-2:]
        if all(f["trophy_rank"] == 1 for f in recent2):
            ms.append("back-to-back Trophy wins going into this TEG")
        if all(f["jacket_rank"] == 1 for f in recent2):
            ms.append("back-to-back Jacket wins going into this TEG")
        if all(f["trophy_rank"] == f["n_players"] for f in recent2):
            ms.append("back-to-back Wooden Spoons going into this TEG")

    # --- Bridesmaid pattern: runner-up ≥ 3 of last 4 TEGs without winning ---
    if tw == 0 and len(last_finishes) >= 3:
        runners_up = sum(1 for f in last_finishes if f["trophy_rank"] == 2)
        if runners_up >= 3:
            ms.append(f"Trophy runner-up in {runners_up} of the last {len(last_finishes)} TEGs without a win")
    if jw == 0 and len(last_finishes) >= 3:
        runners_up = sum(1 for f in last_finishes if f["jacket_rank"] == 2)
        if runners_up >= 3:
            ms.append(f"Jacket runner-up in {runners_up} of the last {len(last_finishes)} TEGs without a win")

    # --- Wooden Spoon magnet: 2+ of last 3 ---
    if len(last_finishes) >= 3:
        recent3 = last_finishes[-3:]
        spoon_recent = sum(1 for f in recent3 if f["trophy_rank"] == f["n_players"])
        if spoon_recent >= 2:
            ms.append(f"Wooden Spoon in {spoon_recent} of the last {len(recent3)} TEGs")

    # --- Last finish for colour ---
    if last_finishes:
        prev = last_finishes[-1]
        prev_teg = prev["teg"]
        n = prev["n_players"]
        if prev["trophy_rank"] == 1:
            ms.append(f"defending Trophy champion (TEG {prev_teg})")
        elif prev["trophy_rank"] == n:
            ms.append(f"reigning Wooden Spoon holder (TEG {prev_teg})")

    return ms


def build_player_cross_teg_history(teg_num: int, df: Optional[pd.DataFrame] = None) -> dict:
    """Cross-TEG history for each player, computed from TEGs strictly before teg_num.

    Returns a dict keyed by full player name:
        {
            "trophy_wins": int,
            "jacket_wins": int,
            "spoon_count": int,
            "last_4_positions": [{"teg": N, "trophy_rank": X, "jacket_rank": Y, "n_players": M}, ...],
            "notable_milestones": [str, ...]
        }

    Pass `df` to avoid re-loading; if omitted, loads via `load_all_data`.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    prior_df = df[df["TEGNum"] < teg_num]
    if prior_df.empty:
        return {}

    from teg_analysis.analysis.history import get_teg_winners
    winners = get_teg_winners(prior_df)  # columns: TEG, Year, TEG Trophy, Green Jacket, HMM Wooden Spoon

    finishes = _compute_teg_finishes(prior_df)

    all_players = sorted(prior_df["Player"].unique())
    out = {}

    for player in all_players:
        trophy_wins = int((winners["TEG Trophy"] == player).sum())
        jacket_wins = int((winners["Green Jacket"] == player).sum())
        spoon_count = int((winners["HMM Wooden Spoon"] == player).sum())

        player_finishes = finishes[finishes["Player"] == player].sort_values("TEGNum")
        last_4 = []
        for _, r in player_finishes.tail(4).iterrows():
            last_4.append({
                "teg": int(r["TEGNum"]),
                "trophy_rank": int(r["trophy_rank"]),
                "jacket_rank": int(r["jacket_rank"]),
                "n_players": int(r["n_players"]),
            })

        wins = {"trophy_wins": trophy_wins, "jacket_wins": jacket_wins, "spoon_count": spoon_count}
        ms = _milestones(player, wins, last_4)

        out[player] = {
            "trophy_wins": trophy_wins,
            "jacket_wins": jacket_wins,
            "spoon_count": spoon_count,
            "last_4_positions": last_4,
            "notable_milestones": ms,
        }

    return out


def build_win_counts(teg_num: int, df: Optional[pd.DataFrame] = None) -> dict:
    """Win counts through and including teg_num (for at-a-glance annotations).

    Returns {player_name: {"trophy_wins": N, "jacket_wins": N, "spoon_count": N}}.
    Used by render.py after the TEG is complete, so includes the current TEG.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    through_df = df[df["TEGNum"] <= teg_num]
    if through_df.empty:
        return {}

    from teg_analysis.analysis.history import get_teg_winners
    winners = get_teg_winners(through_df)

    out = {}
    all_players = sorted(through_df["Player"].unique())
    for player in all_players:
        out[player] = {
            "trophy_wins": int((winners["TEG Trophy"] == player).sum()),
            "jacket_wins": int((winners["Green Jacket"] == player).sum()),
            "spoon_count": int((winners["HMM Wooden Spoon"] == player).sum()),
        }
    return out
