"""
Data processing functions for TEG History analysis.

This module contains functions for:
- Processing winners data and competition statistics  
- Creating winner summary tables and charts data
- Calculating doubles (Trophy + Green Jacket same player/TEG)
"""

import pandas as pd
import altair as alt


def process_winners_for_charts(winners_df):
    """
    Process winners data to create chart-ready datasets for each competition.
    
    Args:
        winners_df (pd.DataFrame): Raw winners data with TEG Trophy, Green Jacket, Wooden Spoon columns
        
    Returns:
        dict: Contains sorted dataframes for each competition and max wins value
        
    Purpose:
        Transforms winners data into format needed for bar charts and tables
        Counts wins per player for each competition type
    """
    # Clean asterisks from winner names (used for footnotes)
    clean_winners = winners_df.replace(r'\*', '', regex=True)
    
    # Melt the DataFrame to long format for easier grouping
    melted_winners = pd.melt(
        clean_winners, 
        id_vars=['TEG'], 
        value_vars=['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'],
        var_name='Competition', 
        value_name='Player'
    )

    # Count wins per player per competition
    player_wins = melted_winners.groupby(['Player', 'Competition']).size().unstack(fill_value=0)
    player_wins = player_wins[['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]
    player_wins.columns = ['Trophy', 'Jacket', 'Spoon']

    # Create sorted dataframes for each competition
    trophy_sorted = player_wins.sort_values(by='Trophy', ascending=False).reset_index()
    jacket_sorted = player_wins.sort_values(by='Jacket', ascending=False).reset_index()
    spoon_sorted = player_wins.sort_values(by='Spoon', ascending=False).reset_index()

    # Find maximum wins for chart scaling
    max_wins = max(
        trophy_sorted['Trophy'].max(), 
        jacket_sorted['Jacket'].max(), 
        spoon_sorted['Spoon'].max()
    )

    return {
        'trophy_sorted': trophy_sorted,
        'jacket_sorted': jacket_sorted, 
        'spoon_sorted': spoon_sorted,
        'max_wins': max_wins
    }


def calculate_trophy_jacket_doubles(winners_df):
    """
    Find players who won both Trophy and Green Jacket in the same TEG.
    
    Args:
        winners_df (pd.DataFrame): Winners data with clean player names (no asterisks)
        
    Returns:
        tuple: (doubles_df, count) where doubles_df shows player doubles and count is total
        
    Purpose:
        Identifies rare achievement of winning both main competitions in single TEG
        Used for "Doubles" tab and statistics display
    """
    # Clean asterisks from winner names
    clean_winners = winners_df.replace(r'\*', '', regex=True)
    
    # Find TEGs where same player won both Trophy and Green Jacket
    same_player_both = clean_winners[clean_winners['TEG Trophy'] == clean_winners['Green Jacket']]
    
    # Count doubles per player
    player_doubles = same_player_both['TEG Trophy'].value_counts().reset_index()
    player_doubles.columns = ['Player', 'Doubles']
    player_doubles = player_doubles.sort_values(by='Doubles', ascending=False)
    
    return player_doubles, same_player_both.shape[0]


def prepare_history_table_display(winners_df):
    """
    Prepare winners data for historical display table.
    
    Args:
        winners_df (pd.DataFrame): Raw winners data with Year and TEG columns
        
    Returns:
        pd.DataFrame: Formatted table with combined TEG(Year) column and Area
        
    Purpose:
        Creates compact historical view combining TEG name and year
        Adds Area as second column based on TEG lookup
    """
    from utils import read_file, ROUND_INFO_CSV  # Import here to avoid circular imports
    
    # Create a copy to avoid modifying original
    display_winners = winners_df.copy()
    
    # Get unique TEG-Area combinations from round_info
    round_info = read_file(ROUND_INFO_CSV)
    teg_areas = round_info[['TEG', 'Area']].drop_duplicates()
    
    # Join area data to winners table
    display_winners = display_winners.merge(teg_areas, on='TEG', how='left')
    
    # Combine TEG and Year into single display column
    display_winners["TEG"] = (
        display_winners['TEG'].astype(str) + " (" + 
        display_winners['Year'].astype(str) + ")"
    )
    
    # Remove separate Year column and reorder columns
    display_winners = display_winners.drop(columns=['Year'])
    
    # Reorder columns: TEG, Area, then competition winners
    competition_cols = [col for col in display_winners.columns if col not in ['TEG', 'Area']]
    column_order = ['TEG', 'Area'] + competition_cols
    display_winners = display_winners[column_order]
    
    return display_winners

def create_bar_chart(df, x_col, y_col, title):
    """
    Create horizontal bar chart for competition wins.
    
    Args:
        df (pd.DataFrame): Data with player and win count columns
        x_col (str): Column name for x-axis (win counts)
        y_col (str): Column name for y-axis (player names)  
        title (str): Chart title
        
    Returns:
        alt.Chart: Altair chart object ready for display
        
    Purpose:
        Standardized chart creation for Trophy, Green Jacket, and Wooden Spoon wins
        Creates horizontal bars with value labels
    """
    # Create base bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X(x_col, title=None, axis=alt.Axis(grid=False, labels=False, domain=False)),
        y=alt.Y(y_col, sort='-x', title=None),
    ).properties(
        title=title,
        height=320
    )
    
    # Add text labels showing win counts
    text = chart.mark_text(align='left', baseline='middle', dx=3).encode(text=x_col)
    
    # Combine chart and text labels
    return chart + text