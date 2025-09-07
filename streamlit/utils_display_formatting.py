"""
Display formatting utilities for TEG data analysis.

Functions for HTML generation, value formatting, and display styling.
These functions provide formatting and display functionality used throughout the codebase.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# Import helper utilities for dependencies
from utils_helper_utilities import get_base_directory

# Configure logging
import logging
logger = logging.getLogger(__name__)

def format_vs_par(value: float) -> str:
    """
    Format the value against par.

    Parameters:
        value (float): The value to format.

    Returns:
        str: Formatted string.
        
    Purpose:
        Formats golf scores relative to par for display (e.g., +2, -1, =).
        Used by analysis and display pages throughout the application.
    """
    value = int(value)
    if value > 0:
        return f"+{value}"
    elif value < 0:
        return f"{value}"
    else:
        return "="

def ordinal(n):
    """
    Convert a number to its ordinal representation.
    
    Parameters:
        n: Number to convert
        
    Returns:
        str: Ordinal string (e.g., 1st, 2nd, 3rd, 11th)
        
    Purpose:
        Provides ordinal number formatting for rankings and positions.
        Used by statistical analysis and display functions.
    """
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix

def safe_ordinal(n):
    """
    Safely convert a number to its ordinal representation, handling NaN and invalid inputs.
    
    Parameters:
        n: Number to convert (may be NaN or invalid)
        
    Returns:
        str: Ordinal string or original value if invalid
        
    Purpose:
        Provides safe ordinal number formatting that handles missing or invalid data.
        Used by statistical analysis functions that may encounter NaN values.
    """
    if pd.isna(n):
        return n  # or return a specific string like 'N/A'
    try:
        return ordinal(int(n))
    except ValueError:
        return str(n)  # or return a specific string for invalid inputs

def format_date_for_scorecard(date_str, input_format=None, output_format='%d/%m/%y'):
    """
    Format date string with flexible input and output formats (UK conventions)
    
    Args:
        date_str: Date string from CSV
        input_format: Optional specific format (e.g., '%d/%m/%Y'). If None, tries common UK formats
        output_format: Output format (default: '15/1/25' UK style without leading zeros)
    
    Returns:
        str: Formatted date or original string if parsing fails
        
    Purpose:
        Formats dates for scorecard display using UK conventions.
        Used by scorecard generation and display pages throughout the application.
    """
    if not date_str or pd.isna(date_str):
        return str(date_str) if date_str else None
    
    date_str = str(date_str).strip()
    
    try:
        if input_format:
            # Use specified format
            date_obj = datetime.strptime(date_str, input_format)
        else:
            # Try common UK date formats (day first, no leading zeros supported)
            uk_formats = [
                '%d/%m/%Y',    # 15/1/2025 or 1/12/2025
                '%d/%m/%y',    # 15/1/25 or 1/12/25
                '%d-%m-%Y',    # 15-1-2025 or 1-12-2025
                '%d-%m-%y',    # 15-1-25 or 1-12-25
                '%d %b %Y',    # 15 Jan 2025
                '%d %B %Y',    # 15 January 2025
                '%Y-%m-%d',    # 2025-01-15 (ISO format)
                '%d.%m.%Y',    # 15.1.2025
                '%d.%m.%y',    # 15.1.25
            ]
            
            date_obj = None
            for fmt in uk_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if date_obj is None:
                return date_str
        
        # Custom formatting to avoid leading zeros in day/month
        if output_format == '%d/%m/%y':
            return f"{date_obj.day}/{date_obj.month}/{date_obj.strftime('%y')}"
        elif output_format == '%d/%m/%Y':
            return f"{date_obj.day}/{date_obj.month}/{date_obj.year}"
        elif output_format == '%d %B %Y':
            return f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}"
        elif output_format == '%d %b %Y':
            return f"{date_obj.day} {date_obj.strftime('%b')} {date_obj.year}"
        elif output_format == '%d %b %y':
            return f"{date_obj.day} {date_obj.strftime('%b')} {date_obj.strftime('%y')}"
        else:
            # For any other format, use standard strftime
            return date_obj.strftime(output_format)
            
    except Exception:
        return date_str

def load_css_file(css_file_path: str):
    """
    Load CSS from file and inject into Streamlit using proper path resolution.
    
    Parameters:
        css_file_path (str): Path to CSS file relative to appropriate directory
        
    Purpose:
        Loads CSS files for styling Streamlit applications.
        Handles path resolution for both development and deployment environments.
    """
    base_dir = get_base_directory()
    
    # If running from streamlit folder, styles are in same folder
    if Path.cwd().name == "streamlit":
        full_path = Path.cwd() / css_file_path
    else:
        # Running from project root, styles are in streamlit subfolder
        full_path = base_dir / "streamlit" / css_file_path
    
    try:
        with open(full_path, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {full_path}")

def load_datawrapper_css():
    """
    Load datawrapper table CSS from external file.
    
    Purpose:
        Loads the main CSS styling for datawrapper tables.
        Most widely used function (22+ files) for consistent table styling.
    """
    load_css_file('styles/datawrapper.css')

def datawrapper_table(df, left_align=None, css_classes=None):
    """
    Render a pandas DataFrame as HTML with datawrapper styling.
    
    Args:
        df: DataFrame to render
        left_align: If True, left-align all cells (backward compatibility)
        css_classes: Additional CSS classes as string (e.g., 'history-table narrow-first')
        
    Purpose:
        Renders DataFrames with consistent datawrapper styling.
        Used by multiple pages for formatted table display.
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
    st.write(df.to_html(index=False, justify='left', classes=classes), unsafe_allow_html=True)

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
    
    Purpose:
        Creates formatted HTML sections for statistical displays.
        Used by analysis pages to show statistics with consistent styling.
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