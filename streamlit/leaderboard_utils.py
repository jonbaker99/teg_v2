import streamlit as st
import pandas as pd
from typing import Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Constants
PLAYER_COLUMN = 'Player'


@st.cache_data
def create_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, ascending: bool = True) -> pd.DataFrame:
    """
    Create a leaderboard from the given dataframe.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe.
        value_column (str): Column to use for ranking.
        ascending (bool): Whether to sort in ascending order.

    Returns:
        pd.DataFrame: Leaderboard dataframe.
    """
    pivot_df = leaderboard_df.pivot_table(
        index=PLAYER_COLUMN, 
        columns='Round', 
        values=value_column, 
        aggfunc='sum', 
        fill_value=0
    ).assign(Total=lambda x: x.sum(axis=1)).sort_values('Total', ascending=ascending)

    pivot_df.columns = [f'R{col}' if isinstance(col, int) else col for col in pivot_df.columns]
    pivot_df = pivot_df.reset_index()
    pivot_df['Rank'] = pivot_df['Total'].rank(method='min', ascending=ascending).astype(int)

    duplicated_scores = pivot_df['Total'].duplicated(keep=False)
    pivot_df.loc[duplicated_scores, 'Rank'] = pivot_df.loc[duplicated_scores, 'Rank'].astype(str) + '='

    columns = ['Rank', PLAYER_COLUMN] + [col for col in pivot_df.columns if col not in ['Rank', PLAYER_COLUMN]]
    leaderboard = pivot_df[columns]
    logger.info(f"Leaderboard created for {value_column}.")
    return leaderboard


def generate_table_html(df: pd.DataFrame) -> str:
    """
    Generate HTML table from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        str: HTML table string.
    """
    html = ["<table class='datawrapper-table narrow-first left-second full-width'>"]
    html.append("<thead><tr><th class='rank-header'></th>" + "".join(f"<th>{col}</th>" for col in df.columns[1:]) + "</tr></thead><tbody>")

    for _, row in df.iterrows():
        row_class = ' class="top-rank"' if str(row['Rank']).startswith('1') else ''
        html.append(f"<tr{row_class}>")
        for col in df.columns:
            cell_class = ' class="total"' if col == 'Total' else ''
            html.append(f'<td{cell_class}>{row[col]}</td>')
        html.append("</tr>")

    html.append("</tbody></table>")
    return "".join(html)


def format_value(value: Any, value_type: str) -> str:
    """
    Format values based on their type.

    Args:
        value (Any): The value to format.
        value_type (str): The type of value ('GrossVP' or 'Stableford').

    Returns:
        str: Formatted value string.
    """
    try:
        num = float(value)
        if value_type == 'GrossVP':
            if num > 0:
                return f"+{int(num)}" if num.is_integer() else f"+{num}"
            elif num < 0:
                return f"{int(num)}" if num.is_integer() else f"{num}"
            else:
                return "="
        elif value_type == 'Stableford':
            return f"{int(round(num))}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value)


def get_champions(df: pd.DataFrame) -> str:
    """
    Get champions from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        str: Comma-separated list of champions.
    """
    champions = df[df['Rank'] == 1][PLAYER_COLUMN].astype(str).tolist()
    return ', '.join(champions)


def get_last_place(df: pd.DataFrame) -> str:
    """
    Get last place players from dataframe (including ties).

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        str: Comma-separated list of last place players.
    """
    df = df.copy()

    # Remove '=' from Rank strings, then convert to numeric
    df['Rank'] = (
        df['Rank']
        .astype(str)           # make sure it's string
        .str.replace("=", "", regex=False)  # drop '=' sign
        .astype(int)           # back to int
    )

    last_rank = df['Rank'].max()
    last_place = df[df['Rank'] == last_rank][PLAYER_COLUMN].astype(str).tolist()
    return ', '.join(last_place)


def display_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, title: str, leader_label: str, ascending: bool) -> None:
    """
    Display a leaderboard.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe.
        value_column (str): Column to use for ranking.
        title (str): Title of the leaderboard.
        leader_label (str): Label for the leader/champion.
        ascending (bool): Whether to sort in ascending order.
    """
    leaderboard = create_leaderboard(leaderboard_df, value_column, ascending)
    champions = get_champions(leaderboard)
    losers = get_last_place(leaderboard)

    columns_to_format = [col for col in leaderboard.columns if col not in ['Rank', PLAYER_COLUMN]]

    for col in columns_to_format:
        leaderboard[col] = leaderboard[col].apply(lambda x: format_value(x, value_column))

    st.markdown(f'#### {title}')

    if value_column == 'Stableford':
        st.markdown(f"""
        <p>{leader_label}: <b>{champions}</b> | Wooden spoon: <b>{losers}</b></p>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <p>{leader_label}: <b>{champions}</b></p>
        """, unsafe_allow_html=True)

    table_html = generate_table_html(leaderboard)
    st.markdown(table_html, unsafe_allow_html=True)