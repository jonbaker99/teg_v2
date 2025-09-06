"""
Data processing functions for course analysis and averages.

This module contains functions for:
- Processing course-specific performance data
- Creating pivot tables for course averages and records
- Handling area filtering and course grouping
- Formatting performance data for display
"""

import pandas as pd
import numpy as np


def prepare_area_filter_options(course_info):
    """
    Prepare area filtering options for course selection.
    
    Args:
        course_info (pd.DataFrame): Course information with areas
        
    Returns:
        tuple: (area_options, all_area_label) for dropdown selection
        
    Purpose:
        Creates consistent area filtering options across course analysis pages
        Includes "ALL AREAS" option for unfiltered data
    """
    unique_areas = sorted(course_info['Area'].unique().tolist())
    all_area_label = 'ALL AREAS'
    area_options = [all_area_label] + unique_areas
    
    return area_options, all_area_label


def filter_data_by_area(all_rd_data, course_info, selected_area, all_area_label):
    """
    Filter round data by selected geographical area.
    
    Args:
        all_rd_data (pd.DataFrame): Complete round data
        course_info (pd.DataFrame): Course information with area mapping
        selected_area (str): Selected area filter
        all_area_label (str): Label for "all areas" option
        
    Returns:
        pd.DataFrame: Filtered round data for selected area
        
    Purpose:
        Enables geographical analysis by filtering to courses in specific areas
        Returns complete dataset when "ALL AREAS" is selected
    """
    if selected_area == all_area_label:
        return all_rd_data
    else:
        # Get courses in the selected area
        courses_in_area = course_info[course_info['Area'] == selected_area]['Course'].tolist()
        
        # Filter round data to only include those courses
        return all_rd_data[all_rd_data['Course'].isin(courses_in_area)]


def calculate_course_round_counts(rd_data):
    """
    Calculate number of rounds played at each course.
    
    Args:
        rd_data (pd.DataFrame): Round data for counting
        
    Returns:
        pd.DataFrame: Course round counts sorted by frequency
        
    Purpose:
        Provides context for course analysis by showing sample sizes
        Helps identify courses with limited data for statistical reliability
    """
    course_count = (
        rd_data[['Course', 'TEG', 'Round']]
        .drop_duplicates()  # Ensure unique combinations of 'Course', 'TEG', 'Round'
        .groupby('Course')  # Group by 'Course'
        .size()  # Count the number of unique 'TEG', 'Round' per 'Course'
        .reset_index(name='Count')  # Reset index and name the count column
        .sort_values(by='Count', ascending=False)  # Sort by 'Count'
    )
    
    return course_count


def create_course_performance_table(df, aggfunc='mean'):
    """
    Create pivot table of course performance by player and aggregation function.
    
    Args:
        df (pd.DataFrame): Round data for analysis
        aggfunc (str): Aggregation function ('mean', 'min', 'max')
        
    Returns:
        pd.DataFrame: Formatted pivot table with performance data
        
    Purpose:
        Creates player-by-course matrix showing performance statistics
        Handles different aggregation types (averages, bests, worsts)
        Formats values appropriately for display (decimals for averages, +/- for vs par)
    """
    round_to = 1 if aggfunc == 'mean' else 0
    
    # Calculate course round counts for sorting
    course_count_df = calculate_course_round_counts(df)
    
    # Create pivot table of GrossVP performance by course and player
    course_data = df.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc=aggfunc)
    course_data.loc[:, course_data.columns != 'Course'] = course_data.loc[:, course_data.columns != 'Course'].round(round_to)
    
    # Calculate overall course totals
    course_total = df.groupby('Course').agg({'GrossVP': aggfunc})
    course_data['Total'] = course_total
    course_data = course_data.reset_index()
    course_data.columns.name = None
    
    # Format numbers for display
    def format_performance_number(x):
        """Format performance values for display with +/- and appropriate precision."""
        if isinstance(x, str):  # Already a string
            return x
        elif pd.isna(x):  # NaN values
            return "-"
        elif x == 0:  # Even par
            return "="
        elif round_to == 0:  # Integer display (min/max)
            return f"{int(x):+d}"
        else:  # Decimal display (averages)
            return f"{x:+.{round_to}f}"
    
    # Apply formatting to all cells
    course_data = course_data.applymap(format_performance_number)
    
    # Merge with round counts and sort by frequency
    course_data = pd.merge(course_data, course_count_df, on='Course').sort_values(by='Count', ascending=False).drop(columns=['Count'])
    
    return course_data


def create_course_summary_table(course_count, mean_data, min_data, max_data):
    """
    Create summary table with course statistics and key performance metrics.
    
    Args:
        course_count (pd.DataFrame): Round counts by course
        mean_data (pd.DataFrame): Average performance data
        min_data (pd.DataFrame): Best performance data  
        max_data (pd.DataFrame): Worst performance data
        
    Returns:
        pd.DataFrame: Summary table with rounds, averages, records, and worst performances
        
    Purpose:
        Provides high-level overview of course difficulty and performance
        Combines key statistics for easy comparison across courses
    """
    summary = course_count.copy()
    summary['Ave'] = mean_data['Total']
    summary['Record'] = min_data['Total']
    summary['Worst'] = max_data['Total']
    summary = summary.rename(columns={'Count': 'Rounds'})
    
    return summary