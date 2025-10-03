import pandas as pd
import numpy as np

def calculate_eclectic_by_dimension(data: pd.DataFrame, dimension: str) -> tuple[pd.DataFrame, str]:
    """Calculates eclectic scores grouped by a specified dimension.

    This function computes the best score for each hole based on a given
    dimension (e.g., 'Player', 'Course'). It handles special cases for 'Teams'
    and 'Combined' dimensions.

    Args:
        data (pd.DataFrame): The input DataFrame with hole-by-hole scores.
        dimension (str): The dimension to group by for the eclectic
            calculation.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: A DataFrame of eclectic scores.
            - str: The display name for the dimension.
    """
    if data.empty:
        return pd.DataFrame()
    
    # Special handling for Teams and Combined dimensions
    if dimension == 'Teams':
        return calculate_team_eclectics(data)
    elif dimension == 'Combined':
        return calculate_combined_eclectic(data)
    
    # Group by dimension and hole, take minimum score
    group_cols = [dimension, 'Hole']
    eclectic_holes = data.groupby(group_cols)['GrossVP'].min().reset_index()
    
    # Count rounds contributing to each dimension's eclectic
    if dimension == 'TEGNum':
        rounds_count = data.groupby(dimension)['Round'].nunique().reset_index()
        rounds_count.rename(columns={'Round': 'Rounds'}, inplace=True)
    else:
        rounds_count = data.groupby(dimension).agg({
            'Round': 'nunique',
            'TEGNum': 'nunique'
        }).reset_index()
    
    # Calculate total rounds per dimension
    if dimension == 'Player':
        # For players: count unique TEG-Round combinations
        rounds_count['Rounds'] = data.groupby(dimension).apply(
            lambda x: len(x[['TEGNum', 'Round']].drop_duplicates())
        ).values
    elif dimension == 'TEGNum':
        # For TEGs: rounds already calculated above
        pass
    elif dimension == 'Course':
        # For courses: count unique TEG-Round combinations
        rounds_count['Rounds'] = data.groupby(dimension).apply(
            lambda x: len(x[['TEGNum', 'Round']].drop_duplicates())
        ).values
    
    # If using TEGNum, create TEG column for display
    display_dimension = dimension
    if dimension == 'TEGNum':
        eclectic_holes['TEG'] = 'TEG ' + eclectic_holes['TEGNum'].astype(str)
        rounds_count['TEG'] = 'TEG ' + rounds_count['TEGNum'].astype(str)
        display_dimension = 'TEG'  # Use TEG for display
    
    # Pivot to get holes as columns
    eclectic_pivot = eclectic_holes.pivot(index=display_dimension, columns='Hole', values='GrossVP')
    
    # Clear the column index name to avoid extra header
    eclectic_pivot.columns.name = None
    
    # Ensure all 18 holes are present
    for hole in range(1, 19):
        if hole not in eclectic_pivot.columns:
            eclectic_pivot[hole] = np.nan
    
    # Sort columns by hole number
    hole_cols = sorted([col for col in eclectic_pivot.columns if isinstance(col, int)])
    eclectic_pivot = eclectic_pivot[hole_cols]
    
    # Calculate total (sum of all holes, ignoring NaN)
    eclectic_pivot['Total'] = eclectic_pivot.sum(axis=1, skipna=True)
    
    # Reset index to make dimension a column
    eclectic_pivot = eclectic_pivot.reset_index()
    
    # Merge with rounds count
    eclectic_pivot = eclectic_pivot.merge(rounds_count[[display_dimension, 'Rounds']], on=display_dimension, how='left')
    
    # Sort by total score (best first)
    eclectic_pivot = eclectic_pivot.sort_values('Total').reset_index(drop=True)
    
    return eclectic_pivot, display_dimension

def calculate_team_eclectics(data: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Calculates eclectic scores for the Heroes vs. Wildcats teams.

    Args:
        data (pd.DataFrame): The input DataFrame with hole-by-hole scores.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: A DataFrame of team eclectic scores.
            - str: The dimension name ('Team').
    """
    # Define team compositions
    heroes = ['Jon BAKER', 'David MULLIN', 'Stuart NEUMANN']
    wildcats = ['Alex BAKER', 'Gregg WILLIAMS', 'John PATTERSON']
    
    # Filter data for team members
    heroes_data = data[data['Player'].isin(heroes)]
    wildcats_data = data[data['Player'].isin(wildcats)]
    
    team_results = []
    
    # Calculate eclectic for each team
    for team_name, team_data in [('Heroes', heroes_data), ('Wildcats', wildcats_data)]:
        if team_data.empty:
            continue
            
        # Get best score for each hole across all team members
        team_eclectic = team_data.groupby('Hole')['GrossVP'].min().reset_index()
        team_eclectic['Team'] = team_name
        
        # Count total rounds for the team
        total_rounds = len(team_data.groupby(['Player', 'TEGNum', 'Round']))
        team_eclectic['Rounds'] = total_rounds
        
        team_results.append(team_eclectic)
    
    if not team_results:
        return pd.DataFrame(), 'Team'
    
    # Combine team results
    all_teams = pd.concat(team_results, ignore_index=True)
    
    # Pivot to get holes as columns
    team_pivot = all_teams.pivot(index='Team', columns='Hole', values='GrossVP')
    team_pivot.columns.name = None
    
    # Ensure all 18 holes are present
    for hole in range(1, 19):
        if hole not in team_pivot.columns:
            team_pivot[hole] = np.nan
    
    # Sort columns by hole number
    hole_cols = sorted([col for col in team_pivot.columns if isinstance(col, int)])
    team_pivot = team_pivot[hole_cols]
    
    # Calculate total
    team_pivot['Total'] = team_pivot.sum(axis=1, skipna=True)
    
    # Reset index and add rounds count
    team_pivot = team_pivot.reset_index()
    
    # Add rounds count for each team
    rounds_data = []
    for team_name, team_data in [('Heroes', heroes_data), ('Wildcats', wildcats_data)]:
        if not team_data.empty:
            rounds_data.append({
                'Team': team_name,
                'Rounds': len(team_data.groupby(['Player', 'TEGNum', 'Round']))
            })
    
    rounds_df = pd.DataFrame(rounds_data)
    team_pivot = team_pivot.merge(rounds_df, on='Team', how='left')
    
    # Sort by total score
    team_pivot = team_pivot.sort_values('Total').reset_index(drop=True)
    
    return team_pivot, 'Team'

def calculate_combined_eclectic(data: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Calculates a single combined eclectic score from all data.

    Args:
        data (pd.DataFrame): The input DataFrame with hole-by-hole scores.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: A DataFrame with the combined eclectic score.
            - str: The dimension name ('Combined').
    """
    if data.empty:
        return pd.DataFrame(), 'Combined'
    
    # Get best score for each hole across ALL data
    combined_eclectic = data.groupby('Hole')['GrossVP'].min()
    
    # Count total rounds
    total_rounds = len(data.groupby(['Player', 'TEGNum', 'Round']))
    
    # Create result dataframe with proper structure
    result_data = []
    
    # Build the row data
    row_data = {'Combined': 'All Data'}
    
    # Add scores for each hole
    for hole in range(1, 19):
        if hole in combined_eclectic.index:
            row_data[hole] = combined_eclectic[hole]
        else:
            row_data[hole] = np.nan
    
    # Calculate total
    hole_scores = [row_data[hole] for hole in range(1, 19) if not pd.isna(row_data[hole])]
    row_data['Total'] = sum(hole_scores)
    row_data['Rounds'] = total_rounds
    
    result_data.append(row_data)
    
    # Create DataFrame
    result_df = pd.DataFrame(result_data)
    
    # Ensure proper column order
    hole_cols = list(range(1, 19))
    ordered_cols = ['Combined', 'Total', 'Rounds'] + hole_cols
    result_df = result_df[ordered_cols]
    
    return result_df, 'Combined'

def format_eclectic_table(eclectic_df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Formats the eclectic table for display.

    Args:
        eclectic_df (pd.DataFrame): The eclectic scores DataFrame.
        dimension (str): The dimension column name.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    if eclectic_df.empty:
        return pd.DataFrame()
    
    # Create display table
    display_df = eclectic_df.copy()
    
    # Rename the dimension column for display
    display_df = display_df.rename(columns={dimension: dimension})
    
    # Convert hole scores to integers where possible, handle NaN
    hole_cols = [col for col in display_df.columns if isinstance(col, int)]
    for col in hole_cols + ['Total']:
        display_df[col] = display_df[col].apply(lambda x: int(x) if pd.notna(x) else '-')
    
    # Ensure Rounds column is integer
    if 'Rounds' in display_df.columns:
        display_df['Rounds'] = display_df['Rounds'].astype(int)
    
    # Reorder columns: dimension, total, rounds, holes 1-18
    ordered_cols = [dimension] + ['Total'] + ['Rounds'] + hole_cols
    display_df = display_df[ordered_cols]
    
    return display_df