import streamlit as st
import pandas as pd
from typing import Any
import logging
from utils import get_net_competition_measure

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
        value_type (str): The type of value ('GrossVP', 'NetVP', or 'Stableford').

    Returns:
        str: Formatted value string.
    """
    try:
        num = float(value)
        if value_type in ['GrossVP', 'NetVP']:
            # Format vs par values with +/- signs
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


def display_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, title: str, leader_label: str, ascending: bool, competition_name: str = None) -> None:
    """
    Display a leaderboard with dynamic title formatting.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe.
        value_column (str): Column to use for ranking.
        title (str): Base title of the leaderboard (used as fallback).
        leader_label (str): Label for the leader/champion.
        ascending (bool): Whether to sort in ascending order.
        competition_name (str): Name of competition (e.g. "Trophy", "Green Jacket") for new title format.
    """
    leaderboard = create_leaderboard(leaderboard_df, value_column, ascending)
    champions = get_champions(leaderboard)
    losers = get_last_place(leaderboard)

    columns_to_format = [col for col in leaderboard.columns if col not in ['Rank', PLAYER_COLUMN]]

    for col in columns_to_format:
        leaderboard[col] = leaderboard[col].apply(lambda x: format_value(x, value_column))

    # Create new title format: "{Competition} Final/Latest Leaderboard"
    if competition_name:
        status_text, is_complete = _get_tournament_status_text(leaderboard_df)
        if is_complete:
            formatted_title = f"{competition_name} Final Leaderboard"
        else:
            formatted_title = f"{competition_name} Latest Leaderboard"
    else:
        # Fallback to original title format
        formatted_title = title

    st.markdown(f'#### {formatted_title}')

    if value_column in ['Stableford', 'NetVP']:
        st.markdown(f"""
        <p>{leader_label}: <b>{champions}</b> | Wooden spoon: <b>{losers}</b></p>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <p>{leader_label}: <b>{champions}</b></p>
        """, unsafe_allow_html=True)

    table_html = generate_table_html(leaderboard)
    st.markdown(table_html, unsafe_allow_html=True)


def display_net_leaderboard(leaderboard_df: pd.DataFrame, base_title: str, leader_label: str) -> None:
    """
    Display a net competition leaderboard with automatic measure detection.
    
    Automatically determines whether to use NetVP or Stableford based on the TEG number
    in the dataset and displays the appropriate leaderboard using new title format.
    
    Args:
        leaderboard_df (pd.DataFrame): Input dataframe containing TEGNum column.
        base_title (str): Base title (e.g., "TEG 15 Trophy Leaderboard").
        leader_label (str): Label for the leader/champion.
    """
    # Determine the TEG number from the data
    if 'TEGNum' not in leaderboard_df.columns:
        # Fallback to Stableford if TEGNum is not available
        logger.warning("TEGNum column not found in leaderboard data. Defaulting to Stableford.")
        measure = 'Stableford'
        ascending = False
    else:
        # Get the TEG number (assume all data is from the same TEG)
        teg_num = leaderboard_df['TEGNum'].iloc[0]
        measure = get_net_competition_measure(teg_num)
        
        # Set sort order based on measure
        if measure == 'NetVP':
            ascending = True
        else:
            ascending = False
    
    # Call the existing display_leaderboard function with TEG Trophy competition name
    display_leaderboard(leaderboard_df, measure, base_title, leader_label, ascending, competition_name="TEG Trophy")


def _get_tournament_status_text(leaderboard_df: pd.DataFrame) -> tuple[str, bool]:
    """
    Get tournament status text and completion status using fast status files.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe with TEG column.

    Returns:
        tuple: (status_text, is_complete) where status_text is the text to use in titles
    """
    from utils import read_file, get_teg_rounds

    # Get TEG name and extract number
    if 'TEG' in leaderboard_df.columns:
        teg_name = leaderboard_df['TEG'].iloc[0]
        teg_num = int(teg_name.split()[-1])  # Extract number from "TEG 18"
    else:
        # Fallback to original method if TEG column not available
        current_rounds = leaderboard_df['Round'].nunique()
        return f"after {current_rounds} round{'s' if current_rounds != 1 else ''}", False

    # Use fast status files to get round count and completion status
    try:
        # Check if TEG is completed
        completed_tegs = read_file('data/completed_tegs.csv')
        if not completed_tegs.empty and teg_num in completed_tegs['TEGNum'].values:
            return "final results", True

        # Check if TEG is in progress
        in_progress_tegs = read_file('data/in_progress_tegs.csv')
        if not in_progress_tegs.empty and teg_num in in_progress_tegs['TEGNum'].values:
            current_rounds = in_progress_tegs[in_progress_tegs['TEGNum'] == teg_num]['Rounds'].iloc[0]
            return f"after {current_rounds} round{'s' if current_rounds != 1 else ''}", False

        # Fallback if not found in status files
        current_rounds = leaderboard_df['Round'].nunique()
        total_rounds = get_teg_rounds(teg_name)
        if current_rounds >= total_rounds:
            return "final results", True
        else:
            return f"after {current_rounds} round{'s' if current_rounds != 1 else ''}", False

    except Exception:
        # Fallback to original method if status files not available
        current_rounds = leaderboard_df['Round'].nunique()
        total_rounds = get_teg_rounds(teg_name)
        if current_rounds >= total_rounds:
            return "final results", True
        else:
            return f"after {current_rounds} round{'s' if current_rounds != 1 else ''}", False