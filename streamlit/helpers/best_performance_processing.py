"""Data processing functions for best TEGs and rounds analysis.

This module contains functions for processing ranked TEG and round data,
creating performance tables with proper formatting, and handling measure name
mappings for the user interface.
"""

import pandas as pd


def get_measure_name_mappings() -> tuple[dict, dict]:
    """Gets mappings between user-friendly and internal measure names.

    This function provides a consistent way to map between the display names
    used in the user interface (e.g., 'Gross') and the internal column names
    used in the data (e.g., 'GrossVP').

    Returns:
        tuple: A tuple containing two dictionaries:
            - name_mapping (dict): Maps user-friendly names to internal names.
            - inverted_mapping (dict): Maps internal names to user-friendly
              names.
    """
    name_mapping = {
        'Gross': 'GrossVP',
        'Score': 'Sc',
        'Net': 'NetVP',
        'Stableford': 'Stableford'
    }
    inverted_mapping = {v: k for k, v in name_mapping.items()}
    
    return name_mapping, inverted_mapping


def prepare_best_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the best TEG performances.

    This function filters and formats the TEG data to create a clean, ranked
    table of the top TEG performances for a selected measure.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of top performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures BEFORE getting best performances
    # (TEG 2 only had 3 rounds, so not comparable to 4-round TEGs)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # For filtered data, we can't use the pre-calculated rankings (they include TEG 2)
    # So we'll get the best scores directly using nsmallest/nlargest
    if selected_measure == 'Stableford':
        # For Stableford, higher is better
        best_tegs = filtered_data.nlargest(n_keep, selected_measure)
    else:
        # For other measures, lower is better
        best_tegs = filtered_data.nsmallest(n_keep, selected_measure)
    
    # Add ranking column manually
    best_tegs = best_tegs.copy()
    best_tegs['#'] = range(1, len(best_tegs) + 1)
    
    # Rename columns for display
    best_tegs = best_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    best_tegs = best_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        best_tegs[selected_friendly_name] = best_tegs[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = best_tegs.select_dtypes(include=['float64', 'int64']).columns
        best_tegs[numeric_columns] = best_tegs[numeric_columns].astype(int)
    
    return best_tegs


def prepare_best_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the best round performances.

    This function filters and formats the round data to create a clean, ranked
    table of the top individual round performances for a selected measure.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of top performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Calculate ranking column name
    rank_measure = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function
    from utils import get_best
    
    best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                   .sort_values(by=rank_measure, ascending=True)
                   .rename(columns={rank_measure: '#'})
                   .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    best_rounds = best_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        best_rounds[selected_friendly_name] = best_rounds[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = best_rounds.select_dtypes(include=['float64', 'int64']).columns
        best_rounds[numeric_columns] = best_rounds[numeric_columns].astype(int)
    
    return best_rounds


def prepare_round_data_with_identifiers(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Prepares round data with combined TEG and round identifiers.

    This function creates a readable round identifier by combining the TEG and
    round number (e.g., "TEG 15|R1").

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing raw ranked round
            data.

    Returns:
        pd.DataFrame: The round data with a formatted 'Round' column.
    """
    rd_data_formatted = rd_data_ranked.copy()
    rd_data_formatted['Round'] = rd_data_formatted['TEG'] + '|R' + rd_data_formatted['Round'].astype(str)
    
    return rd_data_formatted


def prepare_personal_best_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal best TEG performances for each player.

    This function identifies and formats each player's best TEG performance for
    a selected measure, including their overall ranking.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's best TEG
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get each player's best performance from the filtered data using direct sorting
    if selected_measure == 'Stableford':
        # For Stableford, higher is better - get max per player
        personal_best_tegs = filtered_data.loc[filtered_data.groupby('Player')[selected_measure].idxmax()]
    else:
        # For other measures, lower is better - get min per player
        personal_best_tegs = filtered_data.loc[filtered_data.groupby('Player')[selected_measure].idxmin()]
    
    # Sort by the measure (best first)
    sort_ascending = selected_measure != 'Stableford'
    personal_best_tegs = personal_best_tegs.sort_values(by=selected_measure, ascending=sort_ascending)
    
    # Add ranking column manually
    personal_best_tegs = personal_best_tegs.copy()
    personal_best_tegs['#'] = range(1, len(personal_best_tegs) + 1)
    
    # Rename columns for display
    personal_best_tegs = personal_best_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    personal_best_tegs = personal_best_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_best_tegs[selected_friendly_name] = personal_best_tegs[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_best_tegs.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_best_tegs[col] = personal_best_tegs[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_best_tegs.select_dtypes(include=['float64', 'int64']).columns
        personal_best_tegs[numeric_columns] = personal_best_tegs[numeric_columns].astype(int)
    
    return personal_best_tegs


def prepare_personal_best_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal best round performances for each player.

    This function identifies and formats each player's best individual round
    performance for a selected measure, including their overall ranking.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's best round
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Use player-level ranking to get 1 best performance per player
    rank_all_time = f'Rank_within_all_{selected_measure}'
    
    # Get best performances from utils function (player_level=True gets 1 per player)
    from utils import get_best
    
    personal_best_rounds = (get_best(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                           .sort_values(by=rank_all_time, ascending=True)
                           .rename(columns={rank_all_time: '#'})
                           .rename(columns=inverted_name_mapping))
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    personal_best_rounds = personal_best_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_best_rounds[selected_friendly_name] = personal_best_rounds[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_best_rounds.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_best_rounds[col] = personal_best_rounds[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_best_rounds.select_dtypes(include=['float64', 'int64']).columns
        personal_best_rounds[numeric_columns] = personal_best_rounds[numeric_columns].astype(int)
    
    return personal_best_rounds


def prepare_worst_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the worst TEG performances.

    This function filters and formats the TEG data to create a clean, ranked
    table of the worst TEG performances for a selected measure.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of worst performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures BEFORE getting worst performances
    # (TEG 2 only had 3 rounds, so not comparable to 4-round TEGs)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # For filtered data, we can't use get_worst with pre-calculated rankings
    # So we'll get the worst scores directly using nsmallest/nlargest
    if selected_measure == 'Stableford':
        # For Stableford, lower is worse
        worst_tegs = filtered_data.nsmallest(n_keep, selected_measure)
    else:
        # For other measures, higher is worse
        worst_tegs = filtered_data.nlargest(n_keep, selected_measure)
    
    # Add ranking column manually
    worst_tegs = worst_tegs.copy()
    worst_tegs['#'] = range(1, len(worst_tegs) + 1)
    
    # Rename columns for display
    worst_tegs = worst_tegs.rename(columns=inverted_name_mapping)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    worst_tegs = worst_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        worst_tegs[selected_friendly_name] = worst_tegs[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        worst_tegs[numeric_columns] = worst_tegs[numeric_columns].astype(int)
    
    return worst_tegs


def prepare_worst_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str, n_keep: int) -> pd.DataFrame:
    """Creates a formatted table of the worst round performances.

    This function filters and formats the round data to create a clean, ranked
    table of the worst individual round performances for a selected measure.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').
        n_keep (int): The number of worst performances to show.

    Returns:
        pd.DataFrame: A formatted DataFrame ready for display.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Get worst performances from utils function
    from utils import get_worst
    
    worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=False, top_n=n_keep)
                    .rename(columns=inverted_name_mapping))
    
    # Sort by measure in descending order (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    worst_rounds = worst_rounds.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    worst_rounds['#'] = range(1, len(worst_rounds) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    worst_rounds = worst_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation
        worst_rounds[selected_friendly_name] = worst_rounds[selected_friendly_name].apply(format_vs_par)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        worst_rounds[numeric_columns] = worst_rounds[numeric_columns].astype(int)
    
    return worst_rounds


def prepare_personal_worst_teg_table(teg_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal worst TEG performances for each player.

    This function identifies and formats each player's worst TEG performance
    for a selected measure, including their overall ranking.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's worst TEG
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Filter out TEG 2 for all measures (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get worst performances per player using get_worst function 
    from utils import get_worst
    
    personal_worst_tegs = (get_worst(filtered_data, selected_measure, player_level=True, top_n=1)
                          .rename(columns=inverted_name_mapping))
    
    # Sort by measure (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    personal_worst_tegs = personal_worst_tegs.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    personal_worst_tegs['#'] = range(1, len(personal_worst_tegs) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'TEG', 'Area', 'Year']
    personal_worst_tegs = personal_worst_tegs[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_worst_tegs[selected_friendly_name] = personal_worst_tegs[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_worst_tegs[col] = personal_worst_tegs[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_worst_tegs.select_dtypes(include=['float64', 'int64']).columns
        personal_worst_tegs[numeric_columns] = personal_worst_tegs[numeric_columns].astype(int)
    
    return personal_worst_tegs


def prepare_personal_worst_round_table(rd_data_ranked: pd.DataFrame, selected_measure: str, selected_friendly_name: str) -> pd.DataFrame:
    """Creates a formatted table of personal worst round performances for each player.

    This function identifies and formats each player's worst individual round
    performance for a selected measure, including their overall ranking.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.
        selected_measure (str): The internal measure name (e.g., 'GrossVP').
        selected_friendly_name (str): The display name for the measure (e.g.,
            'Gross').

    Returns:
        pd.DataFrame: A formatted DataFrame with each player's worst round
        performance.
    """
    name_mapping, inverted_name_mapping = get_measure_name_mappings()
    
    # Get worst performances per player using get_worst function
    from utils import get_worst
    
    personal_worst_rounds = (get_worst(rd_data_ranked, selected_measure, player_level=True, top_n=1)
                            .rename(columns=inverted_name_mapping))
    
    # Sort by measure (worst first)
    sort_ascending = selected_measure == 'Stableford'  # Stableford: lower is worse
    personal_worst_rounds = personal_worst_rounds.sort_values(by=selected_friendly_name, ascending=sort_ascending)
    
    # Add ranking column
    personal_worst_rounds['#'] = range(1, len(personal_worst_rounds) + 1)
    
    # Select and order columns for display
    display_columns = ['#', 'Player', selected_friendly_name, 'Round', 'Course', 'Year']
    personal_worst_rounds = personal_worst_rounds[display_columns]
    
    # Format vs par columns properly and convert other numeric columns to integers
    from utils import format_vs_par
    
    if selected_friendly_name in ['Gross', 'Net']:
        # Format vs par values with +/- notation (but not the # column)
        personal_worst_rounds[selected_friendly_name] = personal_worst_rounds[selected_friendly_name].apply(format_vs_par)
        # Convert other numeric columns (like #, Year) to integers
        numeric_columns = personal_worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            if col != selected_friendly_name:  # Don't convert the formatted vs par column
                personal_worst_rounds[col] = personal_worst_rounds[col].astype(int)
    else:
        # Convert numeric columns to integers for clean display
        numeric_columns = personal_worst_rounds.select_dtypes(include=['float64', 'int64']).columns
        personal_worst_rounds[numeric_columns] = personal_worst_rounds[numeric_columns].astype(int)
    
    return personal_worst_rounds


def prepare_pb_teg_summary_table(teg_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table of each player's personal best TEG.

    This function generates a summary table showing each player's personal best
    TEG performance across all scoring measures.

    Args:
        teg_data_ranked (pd.DataFrame): DataFrame containing ranked TEG
            performance data.

    Returns:
        pd.DataFrame: A summary DataFrame with columns for Score, Gross v Par,
        Net v Par, and Stableford.
    """
    from utils import format_vs_par
    
    # Filter out TEG 2 (3 rounds vs standard 4)
    filtered_data = teg_data_ranked[teg_data_ranked['TEGNum'] != 2].copy()
    
    # Get unique players
    players = sorted(filtered_data['Player'].unique())
    
    summary_data = []
    
    for player in players:
        player_data = filtered_data[filtered_data['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}
        
        # Score (lowest is best)
        best_score = player_data.loc[player_data['Sc'].idxmin()]
        row['Score'] = f"<span class='pb-score'>{int(best_score['Sc'])}</span><br><span class='pb-when'>{best_score['TEG']}</span>"
        
        # Gross vs Par (lowest is best)
        best_gross = player_data.loc[player_data['GrossVP'].idxmin()]
        row['Gross'] = f"<span class='pb-score'>{format_vs_par(best_gross['GrossVP'])}</span><br><span class='pb-when'>{best_gross['TEG']}</span>"
        
        # Net vs Par (lowest is best)
        best_net = player_data.loc[player_data['NetVP'].idxmin()]
        row['Net'] = f"<span class='pb-score'>{format_vs_par(best_net['NetVP'])}</span><br><span class='pb-when'>{best_net['TEG']}</span>"
        
        # Stableford (highest is best)
        best_stableford = player_data.loc[player_data['Stableford'].idxmax()]
        row['Stfd'] = f"<span class='pb-score'>{int(best_stableford['Stableford'])}</span><br><span class='pb-when'>{best_stableford['TEG']}</span>"
        
        summary_data.append(row)
    
    return pd.DataFrame(summary_data)


def prepare_pb_round_summary_table(rd_data_ranked: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary table of each player's personal best round.

    This function generates a summary table showing each player's personal best
    individual round performance across all scoring measures.

    Args:
        rd_data_ranked (pd.DataFrame): DataFrame containing ranked round
            performance data.

    Returns:
        pd.DataFrame: A summary DataFrame with columns for Score, Gross v Par,
        Net v Par, and Stableford.
    """
    from utils import format_vs_par
    
    # Get unique players
    players = sorted(rd_data_ranked['Player'].unique())
    
    summary_data = []
    
    for player in players:
        player_data = rd_data_ranked[rd_data_ranked['Player'] == player]
        row = {'Player': player.replace(' ', '<br>')}
        
        # Score (lowest is best)
        best_score = player_data.loc[player_data['Sc'].idxmin()]
        row['Score'] = f"<span class='pb-score'>{int(best_score['Sc'])}</span><br><span class='pb-when'>{best_score['TEG']}|R{best_score['Round']}</span>"
        
        # Gross vs Par (lowest is best)
        best_gross = player_data.loc[player_data['GrossVP'].idxmin()]
        row['Gross'] = f"<span class='pb-score'>{format_vs_par(best_gross['GrossVP'])}</span><br><span class='pb-when'>{best_gross['TEG']}|R{best_gross['Round']}</span>"
        
        # Net vs Par (lowest is best)
        best_net = player_data.loc[player_data['NetVP'].idxmin()]
        row['Net'] = f"<span class='pb-score'>{format_vs_par(best_net['NetVP'])}</span><br><span class='pb-when'>{best_net['TEG']}|R{best_net['Round']}</span>"
        
        # Stableford (highest is best)
        best_stableford = player_data.loc[player_data['Stableford'].idxmax()]
        row['Stfd'] = f"<span class='pb-score'>{int(best_stableford['Stableford'])}</span><br><span class='pb-when'>{best_stableford['TEG']}|R{best_stableford['Round']}</span>"
        
        summary_data.append(row)
    
    return pd.DataFrame(summary_data)