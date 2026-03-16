"""Table generation and statistical display utilities.

This module provides functions for generating formatted tables and statistical
displays for the TEG analysis system.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


# === STAT SECTION CREATION ===

def create_stat_section(title, value=None, df=None, divider=None):
    """
    Creates an HTML string representing a stat section with a title, optional value, and details from a DataFrame.

    This function generates a formatted HTML string for displaying statistical information. It includes
    a title, an optional value (typically a score or primary statistic), and detailed information
    from a provided DataFrame. Each row of the DataFrame is formatted into a single line of details.

    Parameters:
    -----------
    title : str
        The title of the stat section.
    value : str or None, optional
        An optional value to be displayed prominently alongside the title. If None, no value is displayed.
    df : pandas.DataFrame or None, optional
        A DataFrame containing the detailed information to be displayed. Each row represents a set of
        details, and each column will be formatted and displayed. If None, no details are displayed.
    divider : str or None, optional
        An optional value to split up the text on the second row

    Returns:
    --------
    str
        An HTML string representing the formatted stat section.

    Notes:
    ------
    - The function assumes that the necessary CSS classes (stat-section, title, value, stat-details)
    are defined in the Streamlit app's stylesheet.
    - Each column in the DataFrame will be wrapped in a <span> tag with a class name matching the column name.
    - All rows from the DataFrame are joined with '<br>' tags for line breaks.

    Example:
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'name': ['John Doe'], 'score': ['95'], 'date': ['2023-05-01']})
    >>> html = create_stat_section("Top Score", "95", df)
    >>> print(html)
    <div class="stat-section">
        <h2><span class='title'>Top Score</span><span class='value'> 95</span></h2>
        <div class="stat-details">
            <strong><span class='name'>John Doe</span></strong> • <span class='score'>95</span> • <span class='date'>2023-05-01</span>
        </div>
    </div>
    """

    if divider is None:
        divider = ''

    # Create the title and value part
    title_html = f"<h2><span class='title'>{title}</span>"
    if value is not None:
        title_html += f"<span class='value'> {value}</span>"
    title_html += "</h2>"

    # Create the details part from the DataFrame
    details_html = ""
    if df is not None and not df.empty:
        rows = []
        for _, row in df.iterrows():
            # Make only the Player element strong
            player_html = f"<strong><span class='Player'>{row['Player']}</span></strong>"
            # Format other elements normally
            other_elements = [
                f"<span class='{col}'>{row[col]}</span>"
                for col in df.columns if col != 'Player'
            ]
            # Join all elements with the divider
            row_elements = [player_html] + other_elements
            row_str = f" {divider}".join(row_elements)
            rows.append(row_str)
        details_html = "<br>".join(rows)

    # Combine all parts
    return f"""
    <div class="stat-section">
        {title_html}
        <div class="stat-details">
            {details_html}
        </div>
    </div>
    """


# === SCORE TYPE ANALYSIS ===

def define_score_types(gross_vp):
    """
    Define score types based on the GrossVP values.

    Args:
    gross_vp (pd.Series): A pandas Series containing GrossVP values.

    Returns:
    dict: A dictionary with counts for each score type.
    """
    return {
        'Pars_or_Better': (gross_vp <= 0).sum(),
        'Birdies': (gross_vp == -1).sum(),
        'Eagles': (gross_vp == -2).sum(),
        'TBPs': (gross_vp > 2).sum()
    }


def apply_score_types(df, groupby_cols=['Player']):
    """
    Apply score type definitions to a DataFrame and return aggregated results.

    Args:
    df (pd.DataFrame): The input DataFrame with a 'GrossVP' column.
    groupby_cols (list): Columns to group by before applying score types.

    Returns:
    pd.DataFrame: Aggregated results with score type counts.
    """
    grouped = df.groupby(groupby_cols).agg({
        'GrossVP': define_score_types
    }).reset_index()

    # Expand the dictionary result into separate columns
    score_columns = ['Pars_or_Better', 'Birdies', 'Eagles', 'TBPs']
    for col in score_columns:
        grouped[col] = grouped['GrossVP'].apply(lambda x: x[col])

    # Drop the original 'GrossVP' column containing the dictionary
    grouped = grouped.drop(columns=['GrossVP'])

    return grouped


def score_type_stats(df=None):
    """Calculate score type statistics for all players.

    Args:
        df (pd.DataFrame, optional): Input data. If None, loads all data.

    Returns:
        pd.DataFrame: Statistics showing score counts and rates for each player.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data(exclude_teg_50=True)

    # Apply score types grouped by Player
    stats = apply_score_types(df, groupby_cols=['Player'])

    # Add Holes_Played column
    stats['Holes_Played'] = df.groupby('Player')['GrossVP'].count().values

    # Calculate ratios and their inverses
    stats['Birdie_Rate'] = stats['Birdies'] / stats['Holes_Played']
    stats['Holes_per_Birdie'] = stats['Holes_Played'] / stats['Birdies']

    stats['Eagle_Rate'] = stats['Eagles'] / stats['Holes_Played']
    stats['Holes_per_Eagle'] = stats['Holes_Played'] / stats['Eagles']

    stats['TBP_Rate'] = stats['TBPs'] / stats['Holes_Played']
    stats['Holes_per_TBP'] = stats['Holes_Played'] / stats['TBPs']

    stats['Pars_or_Better_Rate'] = stats['Pars_or_Better'] / stats['Holes_Played']
    stats['Holes_per_Par_or_Better'] = stats['Holes_Played'] / stats['Pars_or_Better']

    return stats


def max_scoretype_per_round(df=None):
    """Find maximum score type counts per round for each player.

    Args:
        df (pd.DataFrame, optional): Input data. If None, loads all data.

    Returns:
        pd.DataFrame: Maximum score counts by player.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Apply score types with grouping by Player, Round, and TEG
    scores = apply_score_types(df, groupby_cols=['Player', 'Round', 'TEG'])

    # Find the maximum scores across rounds and TEGs for each player
    max_scores = scores.groupby('Player').agg({
        'Pars_or_Better': 'max',
        'Birdies': 'max',
        'Eagles': 'max',
        'TBPs': 'max'
    }).reset_index()

    return max_scores


def max_scoretype_per_teg(df=None):
    """Find maximum score type counts per TEG for each player.

    Args:
        df (pd.DataFrame, optional): Input data. If None, loads all data.

    Returns:
        pd.DataFrame: Maximum score counts by player.
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Apply score types with grouping by Player and TEG
    scores = apply_score_types(df, groupby_cols=['Player', 'TEG'])

    # Find the maximum scores across TEGs for each player
    max_scores = scores.groupby('Player').agg({
        'Pars_or_Better': 'max',
        'Birdies': 'max',
        'Eagles': 'max',
        'TBPs': 'max'
    }).reset_index()

    return max_scores


# === DATAWRAPPER TABLE RENDERING ===

def datawrapper_table(df, left_align=None, css_classes=None, return_html=True):
    """
    Render a pandas DataFrame as HTML with datawrapper styling.

    Args:
        df: DataFrame to render
        left_align: If True, left-align all cells (backward compatibility)
        css_classes: Additional CSS classes as string (e.g., 'history-table narrow-first')
        return_html: Kept for backward compatibility, always returns HTML string.

    Returns:
        str: HTML string of the rendered table.
    """

    # Start with base class
    classes = 'datawrapper-table'

    # Add left alignment if needed
    if left_align:
        classes += ' table-left-align'

    # Add any additional classes
    if css_classes:
        classes += f' {css_classes}'

    # Render table
    html = df.to_html(index=False, justify='left', classes=classes)
    return html
