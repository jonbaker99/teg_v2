"""HTML table generation and styling utilities.

This module provides functions for generating formatted HTML tables with CSS styling,
including support for highlighting first-place and last-place cells in ranking tables.
"""

import re
import pandas as pd


def generate_ranking_table_html(df: pd.DataFrame, player_col: str = None) -> str:
    """Generate an HTML table with styling for first-place and last-place ranks.

    This function takes a ranking DataFrame (typically with players as rows and
    tournaments as columns, with rank values as cells) and generates an HTML table
    with CSS classes applied to:
    - First place cells (rank "1" or "1=") get the "first-place" class
    - Last place cells (max rank in each column) get the "last-place" class

    Args:
        df: DataFrame with rankings. Index is typically player names, columns are
            tournament names, values are rank strings (e.g., "1", "2=", "3").
        player_col: Name of the player column (used for detection). If not provided,
                   assumes index contains player names.

    Returns:
        str: HTML table with CSS classes applied to rank cells.

    Example:
        >>> df = pd.DataFrame({
        ...     'TEG 1': ['1', '2', '3'],
        ...     'TEG 2': ['2', '1', '3']
        ... }, index=['Player A', 'Player B', 'Player C'])
        >>> html = generate_ranking_table_html(df)
    """
    # Determine player column name
    if player_col is None:
        player_col = df.index.name if df.index.name else "Player"

    # Ensure index has the player column name
    df_copy = df.copy()
    df_copy.index.name = player_col

    # Reset index to make player names a column
    d = df_copy.reset_index()
    d.index.name = None
    d.columns.name = None

    # Build a DataFrame to track CSS classes for each cell
    classes = pd.DataFrame("", index=d.index, columns=d.columns)

    # Regex pattern for rank cells: "N" or "N=" where N is a number
    rank_pat = re.compile(r"^\d+=?$")

    # Apply classes to each ranking column
    for col in d.columns:
        if col == player_col:
            continue  # Skip player column

        # Convert to string for regex matching
        s = d[col].astype("string")

        # Apply "first-place" class to "1" and "1="
        classes.loc[s.isin(["1", "1="]), col] += " first-place"

        # Apply "last-place" class to max rank in this column
        # Only consider real ranks (N or N=), ignore everything else (including NaN/"-")
        mask_rank = s.str.fullmatch(rank_pat)
        numeric_part = s.where(mask_rank).str.replace("=", "", regex=False)
        num = pd.to_numeric(numeric_part, errors="coerce").astype("Int64")

        if num.notna().any():
            max_rank = int(num.max())
            mask_last = s.isin([str(max_rank), f"{max_rank}="])
            classes.loc[mask_last, col] += " last-place"

    # Build HTML table
    html = '<table style="border-collapse: collapse; font-family: monospace; font-size: 14px;">'

    # Header row
    html += '<tr style="background-color: #f0f0f0;">'
    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;"></th>'
    for col in d.columns:
        if col != player_col:
            html += f'<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">{col}</th>'
    html += '</tr>'

    # Data rows
    for idx, row in d.iterrows():
        html += '<tr>'
        # Player name cell
        html += f'<td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{row[player_col]}</td>'

        # Rank cells with CSS classes
        for col in d.columns:
            if col == player_col:
                continue

            val = row[col]
            cell_class = classes.loc[idx, col].strip()

            # Format value: NaN becomes "-", ranks get wrapped in <span>
            if pd.isna(val):
                cell_content = "-"
            else:
                s = str(val)
                if rank_pat.match(s):
                    cell_content = f'<span>{s}</span>'
                else:
                    cell_content = s

            # Apply class attribute if any classes exist
            class_attr = f' class="{cell_class}"' if cell_class else ""

            html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center;"{class_attr}>{cell_content}</td>'

        html += '</tr>'

    html += '</table>'
    return html
