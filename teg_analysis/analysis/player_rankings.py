"""Player-ranking tables by TEG — the two competitions over time.

Ported from streamlit/player_history.py (no Streamlit dependencies). Builds
per-TEG ranking pivots (players x TEGs, rank values with '=' tie markers) for
the Green Jacket (gross) and TEG Trophy (net) competitions, plus a combined
position-count summary.
"""

import pandas as pd

from .scoring import get_net_competition_measure


def create_teg_ranking_table(
    teg_data: pd.DataFrame,
    scoring_type: str,
    row_dimension: str = "Player",
    col_dimension: str = "TEGNum",
) -> pd.DataFrame:
    """Rank players within each TEG for a single scoring measure.

    Args:
        teg_data: TEG-level data (one row per player per TEG).
        scoring_type: 'Sc', 'GrossVP', 'NetVP' or 'Stableford'.
        row_dimension: 'Player' or 'Pl'.
        col_dimension: 'TEGNum' or 'TEG'.

    Returns:
        DataFrame with players as rows, TEGs as columns and rank strings as
        values (ties suffixed with '='). Missing participation is NaN.
    """
    pivot_df = teg_data.pivot_table(
        index=row_dimension,
        columns=col_dimension,
        values=scoring_type,
        aggfunc="sum",
        fill_value=None,
    )

    # Sort TEG columns numerically (TEG 1, TEG 2, ... not TEG 1, TEG 10, ...)
    if col_dimension == "TEG":
        def teg_sort_key(name):
            try:
                return int(str(name).replace("TEG ", ""))
            except (ValueError, AttributeError):
                return 999
        pivot_df = pivot_df[sorted(pivot_df.columns, key=teg_sort_key)]
    else:
        pivot_df = pivot_df[sorted(pivot_df.columns)]

    # Higher Stableford is better; everything else lower is better
    ascending = scoring_type != "Stableford"

    ranked_df = pivot_df.copy()
    for teg_col in pivot_df.columns:
        col_data = pivot_df[teg_col].dropna()
        if len(col_data) == 0:
            continue

        ranks = col_data.rank(method="min", ascending=ascending).astype(int).astype(str)

        is_tie = col_data.duplicated(keep=False)
        if is_tie.any():
            ranks.loc[is_tie] = ranks.loc[is_tie] + "="

        # Column must be object to hold both NaN and rank strings
        ranked_df[teg_col] = ranked_df[teg_col].astype(object)
        ranked_df.loc[ranks.index, teg_col] = ranks

    ranked_df = ranked_df.reset_index().sort_values(by=row_dimension)
    return ranked_df


def create_net_competition_ranking_table(
    teg_data: pd.DataFrame,
    row_dimension: str = "Player",
    col_dimension: str = "TEGNum",
) -> pd.DataFrame:
    """Ranking table for the TEG Trophy (net), using the right measure per TEG.

    Uses NetVP for TEGs scored on net-vs-par and Stableford for TEG 8+ (per
    ``get_net_competition_measure``), then merges into a single pivot.
    """
    if col_dimension == "TEG":
        unique_tegs = teg_data["TEG"].unique()
        teg_to_num = {f"TEG {num}": num for num in teg_data["TEGNum"].unique()}
    else:
        unique_tegs = teg_data["TEGNum"].unique()
        teg_to_num = {num: num for num in unique_tegs}

    netvp_tegs, stableford_tegs = [], []
    for teg in unique_tegs:
        teg_num = teg_to_num.get(teg, 999)
        if get_net_competition_measure(teg_num) == "NetVP":
            netvp_tegs.append(teg)
        else:
            stableford_tegs.append(teg)

    result_dfs = []
    if netvp_tegs:
        netvp_data = teg_data[teg_data[col_dimension].isin(netvp_tegs)]
        result_dfs.append(create_teg_ranking_table(netvp_data, "NetVP", row_dimension, col_dimension))
    if stableford_tegs:
        stab_data = teg_data[teg_data[col_dimension].isin(stableford_tegs)]
        result_dfs.append(create_teg_ranking_table(stab_data, "Stableford", row_dimension, col_dimension))

    if not result_dfs:
        return pd.DataFrame()
    if len(result_dfs) == 1:
        combined_df = result_dfs[0]
    else:
        combined_df = result_dfs[0]
        for df in result_dfs[1:]:
            combined_df = combined_df.merge(df, on=row_dimension, how="outer")

    # Re-sort TEG columns after the merge
    if col_dimension == "TEG":
        def teg_sort_key(name):
            try:
                return int(str(name).replace("TEG ", ""))
            except (ValueError, AttributeError):
                return 999
        teg_columns = [c for c in combined_df.columns if c != row_dimension]
        combined_df = combined_df[[row_dimension] + sorted(teg_columns, key=teg_sort_key)]
    else:
        teg_columns = [c for c in combined_df.columns if c != row_dimension]
        combined_df = combined_df[[row_dimension] + sorted(teg_columns)]

    return combined_df.sort_values(by=row_dimension).reset_index(drop=True)


def create_combined_position_summary(
    ranked_df: pd.DataFrame, player_col: str = "Player"
) -> pd.DataFrame:
    """Per-player summary: average finishing position, TEGs played, 1st–6th counts.

    Args:
        ranked_df: Output of the ranking-table builders (players x TEGs of rank
            strings).
        player_col: Name of the player column.

    Returns:
        DataFrame with columns ['', 'Ave', 'TEGs', '1st'..'6th'] sorted by
        average position (best first; non-players last).
    """
    rank_columns = [c for c in ranked_df.columns if c != player_col]
    summary_data = []

    for _, row in ranked_df.iterrows():
        positions = row[rank_columns]
        numeric_positions = []
        position_counts = {str(i): 0 for i in range(1, 7)}

        for pos in positions.dropna():
            clean_pos = str(pos).replace("=", "")
            if clean_pos.isdigit():
                numeric_positions.append(int(clean_pos))
                if 1 <= int(clean_pos) <= 6:
                    position_counts[clean_pos] += 1

        if numeric_positions:
            avg_position = sum(numeric_positions) / len(numeric_positions)
            tegs_played = len(numeric_positions)
        else:
            avg_position = float("inf")
            tegs_played = 0

        summary_data.append({
            "": row[player_col],
            "Ave": round(avg_position, 1) if avg_position != float("inf") else None,
            "TEGs": tegs_played,
            "1st": position_counts["1"],
            "2nd": position_counts["2"],
            "3rd": position_counts["3"],
            "4th": position_counts["4"],
            "5th": position_counts["5"],
            "6th": position_counts["6"],
        })

    summary_df = pd.DataFrame(summary_data)
    return summary_df.sort_values("Ave", ascending=True, na_position="last").reset_index(drop=True)
