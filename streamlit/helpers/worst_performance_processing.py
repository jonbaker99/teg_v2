"""Data processing functions for worst performance analysis.

This module contains functions for processing worst performance records,
formatting the data for display, and creating performance stat sections with
proper formatting.
"""

import pandas as pd


def get_performance_measure_titles() -> dict:
    """Defines measure titles for worst performance displays.

    This function provides consistent titles for worst performance statistics
    by separating internal field names from user-facing descriptions.

    Returns:
        dict: A mapping of internal measure names to display titles.
    """
    measure_titles = {
        'Sc': "Worst Score",
        'GrossVP': "Worst Gross",
        'NetVP': "Worst Net",
        'Stableford': "Worst Stableford"
    }
    
    return measure_titles


def format_performance_value(value: float, measure: str) -> str:
    """Formats performance values for display with appropriate notation.

    This function applies consistent formatting for worst performance values,
    using +/- notation for vs-par measures and plain integers for others.

    Args:
        value (float): The performance value to format.
        measure (str): The performance measure type.

    Returns:
        str: The formatted value with +/- notation for vs-par measures.
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +5 or -2
    else:
        return str(int(value))    # Shows 85


def prepare_worst_performance_dataframe(worst_records: pd.DataFrame, record_type: str) -> pd.DataFrame:
    """Prepares the worst performance DataFrame for stat section display.

    This function formats worst performance data for a clean stat section
    display, handling different record types with appropriate column selection
    and creating combined identifiers for rounds and 9-hole segments.

    Args:
        worst_records (pd.DataFrame): The raw worst performance records.
        record_type (str): The type of record ('teg', 'round', or
            'frontback').

    Returns:
        pd.DataFrame: A formatted DataFrame ready for stat section display.
    """
    df = worst_records.copy()
    df['Year'] = df['Year'].astype(str)
    
    if record_type in ['round', 'frontback']:
        # Format round identifier
        df['Round'] = 'R' + df['Round'].astype(str)
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']
        
        # Add front/back identifier for 9-hole records
        if record_type == 'frontback':
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'
        
        # Select columns for round/9-hole display
        df = df[['Player', 'Course', 'TEG_Round', 'Year']]
    else:  # TEG record type
        # Select columns for TEG display
        df = df[['Player', 'TEG', 'Year']]
    
    return df


def load_worst_performance_custom_css() -> str:
    """Loads custom CSS styling for the worst performance page.

    This function provides specialized styling for worst performance displays,
    creating a consistent visual layout for stat sections and defining
    typography and color schemes.

    Returns:
        str: A string of CSS styling for stat sections and layout.
    """
    css_styles = """
    <style>
    div[data-testid="column"] {
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 20px;
        height: 100%;
    }
    .stat-section {
        margin-bottom: 20px;
        background-color: rgb(240, 242, 246);
        padding: 20px;
        margin: 5px;
    }
    .stat-section h2 {
        margin-bottom: 5px;
        font-size: 22px;
        line-height: 1.0;
        color: #333;
        padding: 0;
    }
    .stat-section h2 .title {
        font-weight: normal;
    }
    .stat-section h2 .value {
        font-weight: bold;
    }
    .stat-details {
        font-size: 16px;
        color: #999;
        line-height: 1.4;
    }
    .stat-details .Player {
        color: #666;
    }
    </style>
    """
    
    return css_styles


def create_worst_performance_section(worst_records: pd.DataFrame, measure: str, record_type: str, measure_titles: dict) -> str:
    """Creates a complete worst performance stat section.

    This function generates a complete stat section for the worst performance
    display, combining the title, value, and details into formatted HTML.

    Args:
        worst_records (pd.DataFrame): The worst performance records.
        measure (str): The performance measure.
        record_type (str): The type of record ('teg', 'round', or
            'frontback').
        measure_titles (dict): A dictionary of measure title mappings.

    Returns:
        str: The HTML for the stat section display.
    """
    from utils import create_stat_section
    
    title = measure_titles[measure]
    value = format_performance_value(worst_records[measure].iloc[0], measure)
    df = prepare_worst_performance_dataframe(worst_records, record_type)
    
    return create_stat_section(title, value, df, "| ")


def get_filtered_teg_data() -> pd.DataFrame:
    """Gets TEG data with TEG 2 excluded for worst performance analysis.

    This function excludes TEG 2 from the worst performance analysis as it is
    considered anomalous, providing a clean dataset for meaningful
    comparisons.

    Returns:
        pd.DataFrame: The TEG data with TEG 2 excluded.
    """
    from utils import get_complete_teg_data
    
    teg_data = get_complete_teg_data()
    filtered_teg_data = teg_data[teg_data['TEGNum'] != 2]
    
    return filtered_teg_data