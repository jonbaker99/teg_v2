"""
Data processing functions for worst performance analysis (worst TEGs, rounds, 9s).

This module contains functions for:
- Processing worst performance records across different levels
- Formatting worst performance data for display
- Creating performance stat sections with proper formatting
"""

import pandas as pd


def get_performance_measure_titles():
    """
    Define measure titles for worst performance displays.
    
    Returns:
        dict: Mapping of internal measure names to display titles
        
    Purpose:
        Provides consistent titles for worst performance statistics
        Separates internal field names from user-facing descriptions
    """
    measure_titles = {
        'Sc': "Worst Score",
        'GrossVP': "Worst Gross",
        'NetVP': "Worst Net",
        'Stableford': "Worst Stableford"
    }
    
    return measure_titles


def format_performance_value(value, measure):
    """
    Format performance values for display with appropriate notation.
    
    Args:
        value: Performance value to format
        measure (str): Performance measure type
        
    Returns:
        str: Formatted value with +/- notation for vs-par measures
        
    Purpose:
        Applies consistent formatting for worst performance values
        Uses +/- notation for vs-par measures, plain integers for others
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +5 or -2
    else:
        return str(int(value))    # Shows 85


def prepare_worst_performance_dataframe(worst_records, record_type):
    """
    Prepare worst performance dataframe for stat section display.
    
    Args:
        worst_records (pd.DataFrame): Raw worst performance records
        record_type (str): Type of record ('teg', 'round', 'frontback')
        
    Returns:
        pd.DataFrame: Formatted dataframe ready for stat section display
        
    Purpose:
        Formats worst performance data for clean stat section display
        Handles different record types with appropriate column selection
        Creates combined identifiers for rounds and 9-hole segments
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


def load_worst_performance_custom_css():
    """
    Load custom CSS styling for worst performance page.
    
    Returns:
        str: CSS styling for stat sections and layout
        
    Purpose:
        Provides specialized styling for worst performance displays
        Creates consistent visual layout for stat sections
        Defines typography and color schemes for performance data
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


def create_worst_performance_section(worst_records, measure, record_type, measure_titles):
    """
    Create complete worst performance stat section.
    
    Args:
        worst_records (pd.DataFrame): Worst performance records
        measure (str): Performance measure
        record_type (str): Type of record ('teg', 'round', 'frontback')
        measure_titles (dict): Measure title mappings
        
    Returns:
        str: HTML for stat section display
        
    Purpose:
        Creates complete stat section for worst performance display
        Combines title, value, and details into formatted HTML
        Handles all record types with appropriate formatting
    """
    from utils import create_stat_section
    
    title = measure_titles[measure]
    value = format_performance_value(worst_records[measure].iloc[0], measure)
    df = prepare_worst_performance_dataframe(worst_records, record_type)
    
    return create_stat_section(title, value, df, "| ")


def get_filtered_teg_data():
    """
    Get TEG data with TEG 2 excluded for worst performance analysis.
    
    Returns:
        pd.DataFrame: TEG data with TEG 2 excluded
        
    Purpose:
        Excludes TEG 2 from worst performance analysis as it's considered anomalous
        Provides clean dataset for meaningful worst performance comparisons
    """
    from utils import get_complete_teg_data
    
    teg_data = get_complete_teg_data()
    filtered_teg_data = teg_data[teg_data['TEGNum'] != 2]
    
    return filtered_teg_data