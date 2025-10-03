"""Data processing functions for course analysis and averages.

This module contains functions for processing course-specific performance data,
creating pivot tables for course averages and records, handling area filtering
and course grouping, and formatting performance data for display.
"""

import pandas as pd
import numpy as np


def prepare_area_filter_options(course_info: pd.DataFrame) -> tuple[list, str]:
    """Prepares area filtering options for course selection.

    This function creates a list of unique areas for dropdown selection,
    including an "ALL AREAS" option for unfiltered data.

    Args:
        course_info (pd.DataFrame): DataFrame containing course information
            with an 'Area' column.

    Returns:
        tuple: A tuple containing:
            - area_options (list): A list of area options for dropdown
              selection.
            - all_area_label (str): The label for the "all areas" option.
    """
    unique_areas = sorted(course_info['Area'].unique().tolist())
    all_area_label = 'ALL AREAS'
    area_options = [all_area_label] + unique_areas
    
    return area_options, all_area_label


def filter_data_by_area(all_rd_data: pd.DataFrame, course_info: pd.DataFrame, selected_area: str, all_area_label: str) -> pd.DataFrame:
    """Filters round data by the selected geographical area.

    This function enables geographical analysis by filtering the data to
    courses in a specific area. It returns the complete dataset if "ALL AREAS"
    is selected.

    Args:
        all_rd_data (pd.DataFrame): The complete round data.
        course_info (pd.DataFrame): DataFrame containing course information
            with an 'Area' column.
        selected_area (str): The selected area to filter by.
        all_area_label (str): The label for the "all areas" option.

    Returns:
        pd.DataFrame: The filtered round data for the selected area.
    """
    if selected_area == all_area_label:
        return all_rd_data
    else:
        # Get courses in the selected area
        courses_in_area = course_info[course_info['Area'] == selected_area]['Course'].tolist()
        
        # Filter round data to only include those courses
        return all_rd_data[all_rd_data['Course'].isin(courses_in_area)]


def calculate_course_round_counts(rd_data: pd.DataFrame) -> pd.DataFrame:
    """Calculates the number of rounds played at each course.

    This function provides context for course analysis by showing the sample
    size for each course, which helps in assessing statistical reliability.

    Args:
        rd_data (pd.DataFrame): The round data to be counted.

    Returns:
        pd.DataFrame: A DataFrame with course round counts, sorted by
        frequency.
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


def create_course_performance_table(df: pd.DataFrame, aggfunc: str = 'mean') -> pd.DataFrame:
    """Creates a pivot table of course performance by player.

    This function generates a player-by-course matrix showing performance
    statistics based on the specified aggregation function (e.g., mean, min,
    max).

    Args:
        df (pd.DataFrame): The round data for analysis.
        aggfunc (str, optional): The aggregation function to use ('mean',
            'min', 'max'). Defaults to 'mean'.

    Returns:
        pd.DataFrame: A formatted pivot table with performance data.
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


def create_course_summary_table(course_count: pd.DataFrame, mean_data: pd.DataFrame, min_data: pd.DataFrame, max_data: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table with course statistics and key performance metrics.

    This function provides a high-level overview of course difficulty and
    performance by combining key statistics for easy comparison across courses.

    Args:
        course_count (pd.DataFrame): DataFrame with round counts by course.
        mean_data (pd.DataFrame): DataFrame with average performance data.
        min_data (pd.DataFrame): DataFrame with best performance data.
        max_data (pd.DataFrame): DataFrame with worst performance data.

    Returns:
        pd.DataFrame: A summary table with rounds, averages, records, and
        worst performances.
    """
    summary = course_count.copy()
    summary['Ave'] = mean_data['Total']
    summary['Record'] = min_data['Total']
    summary['Worst'] = max_data['Total']
    summary = summary.rename(columns={'Count': 'Rounds'})
    
    return summary