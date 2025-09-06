"""
Display helper functions for Records pages.

This module contains reusable functions for:
- Value formatting (scores, vs-par displays)
- Data preparation for display
- Constants and mappings for consistent labeling
"""

import pandas as pd


# === CONSTANTS ===
MEASURE_TITLES = {
    'Sc': "Best Score",
    'GrossVP': "Best Gross", 
    'NetVP': "Best Net",
    'Stableford': "Best Stableford"
}


# === FORMATTING FUNCTIONS ===

def format_record_value(value, measure):
    """
    Format a record value for display based on measure type.
    
    Args:
        value: The numeric value to format
        measure: The measure type ('GrossVP', 'NetVP', 'Sc', 'Stableford')
    
    Returns:
        str: Formatted value (e.g., "+3", "-2", "85")
        
    Example:
        format_record_value(3, 'GrossVP') -> "+3"
        format_record_value(-2, 'NetVP') -> "-2" 
        format_record_value(85, 'Sc') -> "85"
    """
    if measure in ['GrossVP', 'NetVP']:
        return f"{int(value):+}"  # Shows +3 or -2
    else:
        return str(int(value))    # Shows 85


def prepare_records_display(best_records, record_type):
    """
    Prepare record data for display by formatting columns and selecting relevant fields.
    
    Args:
        best_records (pd.DataFrame): Raw record data from database
        record_type (str): Type of record - 'teg', 'round', or 'frontback'
        
    Returns:
        pd.DataFrame: Formatted data ready for display
        
    Purpose:
        Different record types need different column combinations:
        - TEG records: Player, TEG, Year
        - Round records: Player, Course, TEG+Round, Year  
        - 9-hole records: Player, Course, TEG+Round+FrontBack, Year
    """
    df = best_records.copy()
    df['Year'] = df['Year'].astype(str)
    
    if record_type in ['round', 'frontback']:
        # Add "R" prefix to round numbers (R1, R2, etc.)
        df['Round'] = 'R' + df['Round'].astype(str)
        # Combine TEG and Round for display (e.g., "TEG 15, R2")
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']
        
        if record_type == 'frontback':
            # Add front/back designation for 9-hole records
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'
        
        # Select columns for round/9-hole display
        df = df[['Player', 'Course', 'TEG_Round', 'Year']]
    else:  
        # TEG-level records only need these columns
        df = df[['Player', 'TEG', 'Year']]
    
    return df