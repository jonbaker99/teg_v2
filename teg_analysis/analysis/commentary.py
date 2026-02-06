"""Commentary generation functions.

This module provides commentary and narrative generation functions
for round summaries, tournament summaries, and event tracking.
"""


import logging
import pandas as pd

from teg_analysis.constants import ROUND_INFO_CSV, STREAKS_PARQUET

logger = logging.getLogger(__name__)


def create_round_summary(all_data_df=None, round_info_df=None):
    """
    Create a comprehensive summary table for each round (unique TEG + Round + Player combination).

    This function calculates and captures the following metrics for each round:
    - Basic round information (TEG, Round, Date, Course, Area, Player)
    - Round scores (Sc, Gross, and Stableford) for full round, front 9, and back 9
    - Cumulative tournament scores
    - Rankings (round-level and cumulative tournament)
    - Gap to leader (before and after round)
    - Lead tracking (holes in lead, leading at start/end, lead gained/lost counts)
    - Historical rankings (rank among player's rounds and all rounds to date)
    - Score type counts (eagles, birdies, pars, etc.)

    Parameters:
        all_data_df (pd.DataFrame, optional): DataFrame from all-data.parquet. If None, will load from file.
        round_info_df (pd.DataFrame, optional): DataFrame from round_info.csv. If None, will load from file.

    Returns:
        pd.DataFrame: Summary table with one row per player per round, containing all calculated metrics.
    """
    logger.info("Creating round summary table.")

    # ========================================
    # 1. LOAD DATA
    # ========================================
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data, read_file


    if all_data_df is None:
        logger.info("Loading all-data.parquet")
        # Must use parquet file as it contains ranking and gap columns
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if round_info_df is None:
        logger.info("Loading round_info.csv")
        round_info_df = read_file(ROUND_INFO_CSV)

    # Ensure data is sorted chronologically
    round_info_df = round_info_df.sort_values(['TEGNum', 'Round'])
    all_data_df = all_data_df.sort_values(['TEGNum', 'Round', 'Hole', 'Pl'])

    # ========================================
    # 2. CALCULATE ROUND-LEVEL SCORES
    # ========================================
    logger.info("Calculating round-level scores")

    # Filter for front 9 and back 9
    front_9 = all_data_df[all_data_df['Hole'] <= 9].copy()
    back_9 = all_data_df[all_data_df['Hole'] > 9].copy()

    # Aggregate scores by player and round
    round_scores = all_data_df.groupby(['TEGNum', 'Round', 'Pl', 'Player']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    round_scores.columns = ['TEGNum', 'Round', 'Pl', 'Player', 'Round_Score_Sc', 'Round_Score_Gross', 'Round_Score_Stableford']

    # Front 9 scores
    front_9_scores = front_9.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    front_9_scores.columns = ['TEGNum', 'Round', 'Pl', 'Front_9_Score_Sc', 'Front_9_Score_Gross', 'Front_9_Score_Stableford']

    # Back 9 scores
    back_9_scores = back_9.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'Sc': 'sum',
        'GrossVP': 'sum',
        'Stableford': 'sum'
    }).reset_index()
    back_9_scores.columns = ['TEGNum', 'Round', 'Pl', 'Back_9_Score_Sc', 'Back_9_Score_Gross', 'Back_9_Score_Stableford']

    # Merge all score components
    summary = round_scores.merge(front_9_scores, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(back_9_scores, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Calculate Front 9 vs Back 9 difference
    summary['Front_9_vs_Back_9_Sc'] = summary['Front_9_Score_Sc'] - summary['Back_9_Score_Sc']
    summary['Front_9_vs_Back_9_Gross'] = summary['Front_9_Score_Gross'] - summary['Back_9_Score_Gross']
    summary['Front_9_vs_Back_9_Stableford'] = summary['Front_9_Score_Stableford'] - summary['Back_9_Score_Stableford']

    # ========================================
    # 3. GET CUMULATIVE SCORES (from hole 18 of each round)
    # ========================================
    logger.info("Extracting cumulative tournament scores")

    # Get the data at hole 18 of each round (end of round snapshot)
    end_of_round = all_data_df[all_data_df['Hole'] == 18].copy()

    cumulative_scores = end_of_round[['TEGNum', 'Round', 'Pl', 'GrossVP Cum TEG', 'Stableford Cum TEG',
                                       'Rank_GrossVP_TEG', 'Rank_Stableford_TEG',
                                       'Gap_GrossVP_TEG', 'Gap_Stableford_TEG']].copy()
    cumulative_scores.columns = ['TEGNum', 'Round', 'Pl',
                                   'Cumulative_Tournament_Score_Gross', 'Cumulative_Tournament_Score_Stableford',
                                   'Cumulative_Tournament_Rank_Gross', 'Cumulative_Tournament_Rank_Stableford',
                                   'Gap_To_Leader_After_Round_Gross', 'Gap_To_Leader_After_Round_Stableford']

    summary = summary.merge(cumulative_scores, on=['TEGNum', 'Round', 'Pl'], how='left')

    # ========================================
    # 4. CALCULATE RANKINGS
    # ========================================
    logger.info("Calculating round rankings")

    # Round-level rankings (based on this round's score only)
    summary['Player_Round_Rank_Gross'] = summary.groupby(['TEGNum', 'Round'])['Round_Score_Gross'].rank(method='min', ascending=True)
    summary['Player_Round_Rank_Stableford'] = summary.groupby(['TEGNum', 'Round'])['Round_Score_Stableford'].rank(method='min', ascending=False)

    # Cumulative tournament rank BEFORE round (from previous round's hole 18)
    # Shift rankings forward by one round within each TEG and player
    summary = summary.sort_values(['TEGNum', 'Pl', 'Round'])
    summary['Cumulative_Tournament_Rank_Before_Round_Gross'] = summary.groupby(['TEGNum', 'Pl'])['Cumulative_Tournament_Rank_Gross'].shift(1)
    summary['Cumulative_Tournament_Rank_Before_Round_Stableford'] = summary.groupby(['TEGNum', 'Pl'])['Cumulative_Tournament_Rank_Stableford'].shift(1)

    # Gap to leader BEFORE round (from previous round's hole 18)
    summary['Gap_To_Leader_Before_Round_Gross'] = summary.groupby(['TEGNum', 'Pl'])['Gap_To_Leader_After_Round_Gross'].shift(1)
    summary['Gap_To_Leader_Before_Round_Stableford'] = summary.groupby(['TEGNum', 'Pl'])['Gap_To_Leader_After_Round_Stableford'].shift(1)

    # ========================================
    # 5. CALCULATE LEAD TRACKING
    # ========================================
    logger.info("Calculating lead tracking metrics")

    # Count holes where player was in lead (rank = 1) during the round
    holes_in_lead = all_data_df.groupby(['TEGNum', 'Round', 'Pl'], as_index=False).apply(
        lambda x: pd.Series({
            'Holes_In_Lead_Gross': (x['Rank_GrossVP_TEG'] == 1).sum(),
            'Holes_In_Lead_Stableford': (x['Rank_Stableford_TEG'] == 1).sum()
        }), include_groups=False
    ).reset_index()

    summary = summary.merge(holes_in_lead, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Leading at start/end of round flags
    summary['Leading_At_Start_Of_Round_Gross'] = (summary['Cumulative_Tournament_Rank_Before_Round_Gross'] == 1).astype(int)
    summary['Leading_At_Start_Of_Round_Stableford'] = (summary['Cumulative_Tournament_Rank_Before_Round_Stableford'] == 1).astype(int)
    summary['Leading_At_End_Of_Round_Gross'] = (summary['Cumulative_Tournament_Rank_Gross'] == 1).astype(int)
    summary['Leading_At_End_Of_Round_Stableford'] = (summary['Cumulative_Tournament_Rank_Stableford'] == 1).astype(int)

    # ========================================
    # 6. CALCULATE HISTORICAL RANKINGS (CHRONOLOGICAL)
    # ========================================
    logger.info("Calculating historical rankings")

    # Merge with round_info to get dates for chronological ordering
    summary = summary.merge(round_info_df[['TEGNum', 'Round', 'Date']], on=['TEGNum', 'Round'], how='left')

    # Convert date to datetime for proper sorting
    summary['Date'] = pd.to_datetime(summary['Date'], format='%d/%m/%Y', errors='coerce')
    summary = summary.sort_values(['Date', 'TEGNum', 'Round', 'Pl'])

    # For each round, rank it among all player's rounds TO DATE (excluding future rounds)
    # OPTIMIZATION: Simplified approach - rank by cumulative date order without copying data
    logger.info("Calculating historical rankings (simplified vectorized)")

    summary = summary.reset_index(drop=True)

    # Initialize columns
    summary['Round_Rank_In_Player_History_Gross'] = None
    summary['Round_Rank_In_Player_History_Stableford'] = None
    summary['Total_Player_Rounds_To_Date'] = None
    summary['Round_Rank_In_All_History_Gross'] = None
    summary['Round_Rank_In_All_History_Stableford'] = None
    summary['Total_Rounds_To_Date'] = None

    # Create mapping of unique dates sorted chronologically
    unique_dates_sorted = sorted(summary['Date'].dropna().unique())
    date_to_cumcount = {date: i for i, date in enumerate(unique_dates_sorted)}

    # Add cumulative date index
    summary['date_cumindex'] = summary['Date'].map(date_to_cumcount)

    # For each row, calculate rankings efficiently
    for idx, row in summary.iterrows():
        current_date_idx = row['date_cumindex']
        current_player = row['Pl']

        if pd.isna(current_date_idx):
            continue

        # Get all rows up to current date for this player
        player_to_date = summary[(summary['Pl'] == current_player) & (summary['date_cumindex'] <= current_date_idx)]

        if len(player_to_date) > 0:
            # Rank within player's historical data
            player_rank_gross = player_to_date['Round_Score_Gross'].rank(method='min', ascending=True).loc[idx]
            player_rank_stableford = player_to_date['Round_Score_Stableford'].rank(method='min', ascending=False).loc[idx]
            player_total = len(player_to_date)

            summary.at[idx, 'Round_Rank_In_Player_History_Gross'] = f"{int(player_rank_gross)} of {player_total}"
            summary.at[idx, 'Round_Rank_In_Player_History_Stableford'] = f"{int(player_rank_stableford)} of {player_total}"
            summary.at[idx, 'Total_Player_Rounds_To_Date'] = player_total

        # Get all rows up to current date across all players
        all_to_date = summary[summary['date_cumindex'] <= current_date_idx]

        if len(all_to_date) > 0:
            # Rank within all historical data
            all_rank_gross = all_to_date['Round_Score_Gross'].rank(method='min', ascending=True).loc[idx]
            all_rank_stableford = all_to_date['Round_Score_Stableford'].rank(method='min', ascending=False).loc[idx]
            all_total = len(all_to_date)

            summary.at[idx, 'Round_Rank_In_All_History_Gross'] = f"{int(all_rank_gross)} of {all_total}"
            summary.at[idx, 'Round_Rank_In_All_History_Stableford'] = f"{int(all_rank_stableford)} of {all_total}"
            summary.at[idx, 'Total_Rounds_To_Date'] = all_total

    # Drop helper column
    summary = summary.drop('date_cumindex', axis=1)

    # ========================================
    # 7. CALCULATE SCORE TYPE COUNTS
    # ========================================
    logger.info("Calculating score type counts")

    # Count various score types by round
    score_counts = all_data_df.groupby(['TEGNum', 'Round', 'Pl']).agg({
        'GrossVP': [
            ('Eagles_Count', lambda x: (x == -2).sum()),
            ('Birdies_Count', lambda x: (x == -1).sum()),
            ('Pars_Or_Better_Count', lambda x: (x <= 0).sum()),
            ('Triple_Bogeys_Or_Worse_Count', lambda x: (x >= 3).sum())
        ],
        'Stableford': [
            ('Zero_Stableford_Points_Count', lambda x: (x == 0).sum()),
            ('Four_Plus_Stableford_Points_Count', lambda x: (x >= 4).sum()),
            ('Five_Plus_Stableford_Points_Count', lambda x: (x >= 5).sum())
        ]
    }).reset_index()

    # Flatten multi-level columns
    score_counts.columns = ['TEGNum', 'Round', 'Pl', 'Eagles_Count', 'Birdies_Count',
                            'Pars_Or_Better_Count', 'Triple_Bogeys_Or_Worse_Count',
                            'Zero_Stableford_Points_Count', 'Four_Plus_Stableford_Points_Count',
                            'Five_Plus_Stableford_Points_Count']

    summary = summary.merge(score_counts, on=['TEGNum', 'Round', 'Pl'], how='left')

    # ========================================
    # 8. CALCULATE LEAD GAINED/LOST COUNTS FROM EVENTS
    # ========================================
    logger.info("Calculating lead gained/lost counts from events")

    # Generate events data
    events_df = create_round_events(all_data_df=all_data_df)

    # Count how many times each player took/lost lead in each round
    # Filter for lead change events only (exclude hole 1 where taking lead is just starting)
    lead_changes = events_df[events_df['Hole'] > 1].copy()

    # Count lead gains and losses by round for Gross
    lead_gained_gross = lead_changes[lead_changes['Event'] == 'Took Lead (Gross)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Gained_Count_Gross')

    lead_lost_gross = lead_changes[lead_changes['Event'] == 'Lost Lead (Gross)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Lost_Count_Gross')

    # Count lead gains and losses by round for Stableford
    lead_gained_stableford = lead_changes[lead_changes['Event'] == 'Took Lead (Stableford)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Gained_Count_Stableford')

    lead_lost_stableford = lead_changes[lead_changes['Event'] == 'Lost Lead (Stableford)'].groupby(
        ['TEGNum', 'Round', 'Pl']
    ).size().reset_index(name='Lead_Lost_Count_Stableford')

    # Merge lead change counts into summary
    summary = summary.merge(lead_gained_gross, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_lost_gross, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_gained_stableford, on=['TEGNum', 'Round', 'Pl'], how='left')
    summary = summary.merge(lead_lost_stableford, on=['TEGNum', 'Round', 'Pl'], how='left')

    # Fill NaN with 0 (no lead changes)
    summary['Lead_Gained_Count_Gross'] = summary['Lead_Gained_Count_Gross'].fillna(0).astype(int)
    summary['Lead_Lost_Count_Gross'] = summary['Lead_Lost_Count_Gross'].fillna(0).astype(int)
    summary['Lead_Gained_Count_Stableford'] = summary['Lead_Gained_Count_Stableford'].fillna(0).astype(int)
    summary['Lead_Lost_Count_Stableford'] = summary['Lead_Lost_Count_Stableford'].fillna(0).astype(int)

    # ========================================
    # 9. ADD ROUND METADATA
    # ========================================
    logger.info("Adding round metadata from round_info")

    # Merge with round_info for Course, Area, and Year (Date already merged)
    summary = summary.merge(round_info_df[['TEGNum', 'Round', 'Course', 'Area', 'TEG', 'Year']],
                           on=['TEGNum', 'Round'], how='left')

    # ========================================
    # 9. REORDER COLUMNS FOR CLARITY
    # ========================================
    logger.info("Reordering columns")

    # Define column order
    column_order = [
        'TEG', 'TEGNum', 'Round', 'Date', 'Course', 'Area', 'Year', 'Player',
        # Round Scores - Actual Score
        'Round_Score_Sc', 'Front_9_Score_Sc', 'Back_9_Score_Sc', 'Front_9_vs_Back_9_Sc',
        # Round Scores - Gross
        'Round_Score_Gross', 'Front_9_Score_Gross', 'Back_9_Score_Gross', 'Front_9_vs_Back_9_Gross',
        # Round Scores - Stableford
        'Round_Score_Stableford', 'Front_9_Score_Stableford', 'Back_9_Score_Stableford', 'Front_9_vs_Back_9_Stableford',
        # Cumulative Scores
        'Cumulative_Tournament_Score_Gross', 'Cumulative_Tournament_Score_Stableford',
        # Rankings - Gross
        'Player_Round_Rank_Gross', 'Cumulative_Tournament_Rank_Before_Round_Gross', 'Cumulative_Tournament_Rank_Gross',
        # Rankings - Stableford
        'Player_Round_Rank_Stableford', 'Cumulative_Tournament_Rank_Before_Round_Stableford', 'Cumulative_Tournament_Rank_Stableford',
        # Gaps - Gross
        'Gap_To_Leader_Before_Round_Gross', 'Gap_To_Leader_After_Round_Gross',
        # Gaps - Stableford
        'Gap_To_Leader_Before_Round_Stableford', 'Gap_To_Leader_After_Round_Stableford',
        # Lead Tracking - Gross
        'Holes_In_Lead_Gross', 'Leading_At_Start_Of_Round_Gross', 'Leading_At_End_Of_Round_Gross',
        'Lead_Gained_Count_Gross', 'Lead_Lost_Count_Gross',
        # Lead Tracking - Stableford
        'Holes_In_Lead_Stableford', 'Leading_At_Start_Of_Round_Stableford', 'Leading_At_End_Of_Round_Stableford',
        'Lead_Gained_Count_Stableford', 'Lead_Lost_Count_Stableford',
        # Historical Rankings
        'Round_Rank_In_Player_History_Gross', 'Round_Rank_In_Player_History_Stableford',
        'Round_Rank_In_All_History_Gross', 'Round_Rank_In_All_History_Stableford',
        # Score Type Counts
        'Eagles_Count', 'Birdies_Count', 'Pars_Or_Better_Count', 'Triple_Bogeys_Or_Worse_Count',
        'Zero_Stableford_Points_Count', 'Four_Plus_Stableford_Points_Count', 'Five_Plus_Stableford_Points_Count',
        # Support fields
        'Pl', 'Total_Player_Rounds_To_Date', 'Total_Rounds_To_Date'
    ]

    # Reorder columns (keep any extra columns at the end)
    existing_columns = [col for col in column_order if col in summary.columns]
    other_columns = [col for col in summary.columns if col not in column_order]
    summary = summary[existing_columns + other_columns]

    logger.info(f"Round summary table created with {len(summary)} rows and {len(summary.columns)} columns.")

    return summary

# ============================================================================
# SECTION 6B: COMMENTARY - EVENTS & TOURNAMENT (2 HUGE functions)
# ============================================================================
# Tournament-level and event-based analysis
#
# This section contains two monolithic functions for comprehensive tournament
# and event analysis. create_round_events() is 258 lines and performs hole-by-hole
# analysis. create_tournament_summary() is 284 lines and generates tournament-wide
# metrics. Both are computationally expensive with 5-25 second execution times.
# Used for detailed narrative generation and tournament-wide reporting.
#
# KEY FUNCTIONS:
# - create_round_events()       - 258 lines, hole-by-hole event log
# - create_tournament_summary() - 284 lines, tournament metrics
# ============================================================================

def create_round_events(all_data_df=None):
    """
    Create a comprehensive event log capturing key moments during each hole of every round.

    This function tracks two categories of events:

    1. **Position Events** - Changes in tournament standings:
       - Took Lead (Gross/Stableford): Player moved to 1st place
       - Lost Lead (Gross/Stableford): Player dropped from 1st place
       - Hit Bottom (Spoon): Player moved to last place (Stableford-based wooden spoon)
       - Left Bottom (Spoon): Player moved up from last place

    2. **Hole Outcome Events** - Notable scoring achievements:
       - Hole in One, Eagle, Birdie
       - Triple Bogey or Worse, Quintuple Bogey or Worse
       - Zero Points, 4+ Points, 5+ Points (Stableford)

    Parameters:
        all_data_df (pd.DataFrame, optional): DataFrame from all-data.parquet with hole-by-hole rankings.
                                               If None, will load from file.

    Returns:
        pd.DataFrame: Tidy event log with one row per event occurrence.
                     Columns include:
                     - TEG, TEGNum, Round, Hole, Player, Pl
                     - Par, Sc, GrossVP, Stableford
                     - Final_Hole_Flag (boolean)
                     - Event (human-readable description)
                     - Metric (relevant score for the event)
                     - Rank_Gross_Before, Rank_Gross_After
                     - Rank_Stableford_Before, Rank_Stableford_After

    Example:
        >>> events_df = create_round_events()
        >>> events_df[events_df['Event'] == 'Took Lead (Stableford)'].head()
    """
    logger.info("Creating round events log.")

    # ========================================
    # 1. LOAD AND VALIDATE DATA
    # ========================================
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data

    REQUIRED_COLS = [
        'TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player',
        'Sc', 'PAR', 'GrossVP', 'Stableford',
        'Rank_Stableford_TEG', 'Rank_GrossVP_TEG'
    ]

    if all_data_df is None:
        logger.info("Loading all-data.parquet")
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    # Validate required columns
    missing = [c for c in REQUIRED_COLS if c not in all_data_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = all_data_df.copy()

    # ========================================
    # 2. CALCULATE DERIVED FIELDS
    # ========================================
    logger.info("Calculating derived fields")

    # Count players per round (needed for bottom detection)
    n_players = df.groupby(['TEGNum', 'Round'])['Pl'].nunique().rename('NPlayers')
    df = df.merge(n_players, on=['TEGNum', 'Round'], how='left')

    # Create TEG-wide hole index (bridges rounds: R1H18 → R2H1, etc.)
    # Assumes 18 holes per round
    df['TEG_Hole'] = (df['Round'] - 1) * 18 + df['Hole']

    # Derive Wooden Spoon rank (inverse of Stableford rank within each hole)
    # Last place in Stableford = 1st place in Spoon competition
    df = df.sort_values(['TEGNum', 'Round', 'Hole'])
    df['MaxRank_ThisHole'] = df.groupby(['TEGNum', 'Round', 'Hole'])['Rank_Stableford_TEG'].transform('max')
    df['Rank_Spoon_TEG'] = df['MaxRank_ThisHole'] + 1 - df['Rank_Stableford_TEG']

    # ========================================
    # 3. CALCULATE RANK "BEFORE" FIELDS
    # ========================================
    logger.info("Calculating rank before/after fields")

    # Sort by TEG-wide hole order for proper chronological shifting
    df = df.sort_values(['TEGNum', 'Pl', 'TEG_Hole'])

    # Shift rankings by 1 hole to get "before" state (per player, per TEG)
    df['Rank_Gross_After'] = df['Rank_GrossVP_TEG']
    df['Rank_Gross_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_GrossVP_TEG'].shift(1)

    df['Rank_Stableford_After'] = df['Rank_Stableford_TEG']
    df['Rank_Stableford_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_Stableford_TEG'].shift(1)

    df['Rank_Spoon_After'] = df['Rank_Spoon_TEG']
    df['Rank_Spoon_Before'] = df.groupby(['TEGNum', 'Pl'])['Rank_Spoon_TEG'].shift(1)

    # ========================================
    # 4. DETECT POSITION EVENTS (VECTORIZED)
    # ========================================
    logger.info("Detecting position change events")

    position_events_frames = []

    # Define position events for each competition
    position_event_specs = {
        # Gross competition (Green Jacket)
        'Took Lead (Gross)': (
            (df['Rank_Gross_After'] == 1) &
            ((df['Rank_Gross_Before'] > 1) | df['Rank_Gross_Before'].isna())
        ),
        'Lost Lead (Gross)': (
            (df['Rank_Gross_Before'] == 1) &
            (df['Rank_Gross_After'] > 1)
        ),

        # Stableford competition (Trophy)
        'Took Lead (Stableford)': (
            (df['Rank_Stableford_After'] == 1) &
            ((df['Rank_Stableford_Before'] > 1) | df['Rank_Stableford_Before'].isna())
        ),
        'Lost Lead (Stableford)': (
            (df['Rank_Stableford_Before'] == 1) &
            (df['Rank_Stableford_After'] > 1)
        ),

        # Wooden Spoon competition (Stableford-based, last place)
        'Hit Bottom (Spoon)': (
            (df['Rank_Stableford_After'] == df['NPlayers']) &
            ((df['Rank_Stableford_Before'] < df['NPlayers']) | df['Rank_Stableford_Before'].isna())
        ),
        'Left Bottom (Spoon)': (
            (df['Rank_Stableford_Before'] == df['NPlayers']) &
            (df['Rank_Stableford_After'] < df['NPlayers'])
        ),
    }

    # Create wide DataFrame with all position event flags
    position_flags = pd.DataFrame(position_event_specs)

    # Base columns to include in output
    base_cols = ['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                 'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After', 'NPlayers']

    # Reshape to tidy format: one row per event occurrence
    position_events = (
        pd.concat([df[base_cols].reset_index(drop=True), position_flags.reset_index(drop=True)], axis=1)
        .melt(id_vars=base_cols, var_name='Event', value_name='Flag')
        .query('Flag == True')
        .drop(columns='Flag')
    )

    # ========================================
    # 5. DETECT HOLE OUTCOME EVENTS (VECTORIZED)
    # ========================================
    logger.info("Detecting hole outcome events")

    # Sort for consistent ordering with position events
    df_outcomes = df.sort_values(['TEGNum', 'Round', 'Pl', 'TEG_Hole'])

    # Define hole outcome event criteria
    outcome_event_specs = {
        'Hole in One': df_outcomes['Sc'].eq(1),
        'Eagle': df_outcomes['GrossVP'].eq(-2),
        'Birdie': df_outcomes['GrossVP'].eq(-1),
        'Triple Bogey or Worse': df_outcomes['GrossVP'].ge(3),
        'Quintuple Bogey or Worse': df_outcomes['GrossVP'].ge(5),
        'Zero Points': df_outcomes['Stableford'].eq(0),
        '4+ Points': df_outcomes['Stableford'].ge(4),
        '5+ Points': df_outcomes['Stableford'].ge(5),
    }

    # Create wide DataFrame with all outcome event flags
    outcome_flags = pd.DataFrame(outcome_event_specs)

    # Reshape to tidy format
    outcome_events = (
        pd.concat([
            df_outcomes[['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                        'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After',
                        'NPlayers']].reset_index(drop=True),
            outcome_flags.reset_index(drop=True)
        ], axis=1)
        .melt(
            id_vars=['TEGNum', 'TEG', 'Round', 'Hole', 'Pl', 'Player', 'Sc', 'PAR', 'GrossVP', 'Stableford',
                    'Rank_Gross_Before', 'Rank_Gross_After', 'Rank_Stableford_Before', 'Rank_Stableford_After', 'NPlayers'],
            var_name='Event', value_name='Flag'
        )
        .query('Flag == True')
        .drop(columns='Flag')
    )

    # ========================================
    # 6. ADD METRIC COLUMN
    # ========================================
    logger.info("Adding metric column")

    # Map each event type to its relevant metric
    metric_map = {
        'Hole in One': 'Sc',
        'Eagle': 'GrossVP',
        'Birdie': 'GrossVP',
        'Triple Bogey or Worse': 'GrossVP',
        'Quintuple Bogey or Worse': 'GrossVP',
        'Zero Points': 'Stableford',
        '4+ Points': 'Stableford',
        '5+ Points': 'Stableford',
        # Position events don't have a specific metric
        'Took Lead (Gross)': None,
        'Lost Lead (Gross)': None,
        'Took Lead (Stableford)': None,
        'Lost Lead (Stableford)': None,
        'Hit Bottom (Spoon)': None,
        'Left Bottom (Spoon)': None,
    }

    # Combine position and outcome events
    all_events = pd.concat([position_events, outcome_events], ignore_index=True)

    # Add Metric column based on event type
    all_events['Metric'] = all_events.apply(
        lambda row: row[metric_map[row['Event']]] if metric_map.get(row['Event']) else pd.NA,
        axis=1
    )

    # ========================================
    # 7. ADD FINAL HOLE FLAG
    # ========================================
    logger.info("Adding final hole flag")

    all_events['Final_Hole_Flag'] = (all_events['Hole'] == 18)

    # ========================================
    # 8. FORMAT AND RETURN
    # ========================================
    logger.info("Formatting output")

    # Define final column order
    output_cols = [
        'TEG', 'TEGNum', 'Round', 'Hole', 'Player', 'Pl',
        'Par', 'Sc', 'GrossVP', 'Stableford',
        'Final_Hole_Flag', 'Event', 'Metric',
        'Rank_Gross_Before', 'Rank_Gross_After',
        'Rank_Stableford_Before', 'Rank_Stableford_After'
    ]

    # Rename PAR to Par for consistency
    all_events = all_events.rename(columns={'PAR': 'Par'})

    # Select and reorder columns
    events_output = all_events[output_cols].copy()

    # Sort by TEG, Round, Hole, Event, Player for logical ordering
    events_output = events_output.sort_values(
        ['TEGNum', 'Round', 'Hole', 'Event', 'Pl']
    ).reset_index(drop=True)

    logger.info(f"Round events log created with {len(events_output)} event occurrences.")

    return events_output


def create_tournament_summary(all_data_df=None, round_info_df=None):
    """
    Create a comprehensive summary table for each tournament (unique TEG + Player combination).

    This function aggregates round-level data to provide tournament-wide metrics including:
    - Final scores and rankings
    - Performance consistency metrics
    - Lead tracking across all rounds
    - Scoring achievement counts
    - Historical context

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data including rankings.
            If None, loads from all-data.parquet.
        round_info_df (pd.DataFrame, optional): DataFrame with round metadata.
            If None, loads from round_info.csv.

    Returns:
        pd.DataFrame: Summary table with one row per player per TEG, containing all calculated metrics.
    """

    logger.info("Creating tournament summary")

    # ========================================
    # 1. LOAD DATA
    # ========================================
    # Import here to avoid circular dependency
    from teg_analysis.core.data_loader import load_all_data, read_file


    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if round_info_df is None:
        round_info_df = read_file(ROUND_INFO_CSV)

    # Get round summary data for aggregation
    round_summary_df = create_round_summary(all_data_df=all_data_df, round_info_df=round_info_df)

    # ========================================
    # 2. BASIC INFO
    # ========================================
    logger.info("Calculating basic tournament info")

    # Get unique TEG info per player
    basic_info = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Player': 'first',
        'TEG': 'first',
        'Year': 'first'
    }).reset_index()

    # ========================================
    # 3. TOURNAMENT SCORES & RANKINGS
    # ========================================
    logger.info("Calculating tournament scores and rankings")

    # Sum scores across all rounds
    tournament_scores = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Sc': 'sum',
        'Round_Score_Gross': 'sum',
        'Round_Score_Stableford': 'sum'
    }).reset_index()

    tournament_scores.rename(columns={
        'Round_Score_Sc': 'Tournament_Score_Sc',
        'Round_Score_Gross': 'Tournament_Score_Gross',
        'Round_Score_Stableford': 'Tournament_Score_Stableford'
    }, inplace=True)

    # Calculate final rankings within each TEG
    tournament_scores['Final_Rank_Gross'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Gross'].rank(method='min').astype(int)
    tournament_scores['Final_Rank_Stableford'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Stableford'].rank(method='min', ascending=False).astype(int)

    # Calculate gaps to winner
    tournament_scores['Winner_Score_Gross'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Gross'].transform('min')
    tournament_scores['Winner_Score_Stableford'] = tournament_scores.groupby('TEGNum')['Tournament_Score_Stableford'].transform('max')
    tournament_scores['Final_Gap_Gross'] = tournament_scores['Tournament_Score_Gross'] - tournament_scores['Winner_Score_Gross']
    tournament_scores['Final_Gap_Stableford'] = tournament_scores['Winner_Score_Stableford'] - tournament_scores['Tournament_Score_Stableford']

    # Tournament outcome flags
    tournament_scores['Won_Gross'] = tournament_scores['Final_Rank_Gross'] == 1
    tournament_scores['Won_Stableford'] = tournament_scores['Final_Rank_Stableford'] == 1

    # Wooden Spoon: last place in Stableford
    tournament_scores['Max_Rank_Stableford'] = tournament_scores.groupby('TEGNum')['Final_Rank_Stableford'].transform('max')
    tournament_scores['Wooden_Spoon'] = tournament_scores['Final_Rank_Stableford'] == tournament_scores['Max_Rank_Stableford']

    # Margin of victory/defeat (positive if won, negative if lost)
    tournament_scores['Margin_Gross'] = -tournament_scores['Final_Gap_Gross']  # Invert so winner has positive margin
    tournament_scores['Margin_Stableford'] = tournament_scores['Final_Gap_Stableford']  # Already correct direction

    # Drop intermediate columns
    tournament_scores.drop(columns=['Winner_Score_Gross', 'Winner_Score_Stableford', 'Max_Rank_Stableford'], inplace=True)

    # ========================================
    # 4. PERFORMANCE CONSISTENCY
    # ========================================
    logger.info("Calculating performance consistency metrics")

    # Best/worst rounds
    consistency = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Gross': ['min', 'max'],
        'Round_Score_Stableford': ['min', 'max']
    }).reset_index()

    consistency.columns = ['TEGNum', 'Pl',
                          'Best_Round_Gross', 'Worst_Round_Gross',
                          'Worst_Round_Stableford', 'Best_Round_Stableford']

    # Range (best - worst)
    consistency['Range_Round_Gross'] = consistency['Worst_Round_Gross'] - consistency['Best_Round_Gross']
    consistency['Range_Round_Stableford'] = consistency['Best_Round_Stableford'] - consistency['Worst_Round_Stableford']

    # Calculate standard deviation by round and by hole across tournament
    round_std = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Round_Score_Gross': 'std',
        'Round_Score_Stableford': 'std'
    }).reset_index()

    round_std.rename(columns={
        'Round_Score_Gross': 'StdDev_Round_Gross',
        'Round_Score_Stableford': 'StdDev_Round_Stableford'
    }, inplace=True)

    hole_std = all_data_df.groupby(['TEGNum', 'Pl']).agg({
        'GrossVP': 'std',
        'Stableford': 'std'
    }).reset_index()

    hole_std.rename(columns={
        'GrossVP': 'StdDev_Hole_Gross',
        'Stableford': 'StdDev_Hole_Stableford'
    }, inplace=True)

    consistency = consistency.merge(round_std, on=['TEGNum', 'Pl'], how='left')
    consistency = consistency.merge(hole_std, on=['TEGNum', 'Pl'], how='left')

    # ========================================
    # 5. LEAD TRACKING ACROSS TOURNAMENT
    # ========================================
    logger.info("Calculating lead tracking metrics")

    # Total holes in lead
    lead_tracking = round_summary_df.groupby(['TEGNum', 'Pl']).agg({
        'Holes_In_Lead_Gross': 'sum',
        'Holes_In_Lead_Stableford': 'sum',
        'Leading_At_End_Of_Round_Gross': 'sum',
        'Leading_At_End_Of_Round_Stableford': 'sum',
        'Lead_Gained_Count_Gross': 'sum',
        'Lead_Lost_Count_Gross': 'sum',
        'Lead_Gained_Count_Stableford': 'sum',
        'Lead_Lost_Count_Stableford': 'sum'
    }).reset_index()

    lead_tracking.rename(columns={
        'Holes_In_Lead_Gross': 'Total_Holes_In_Lead_Gross',
        'Holes_In_Lead_Stableford': 'Total_Holes_In_Lead_Stableford',
        'Leading_At_End_Of_Round_Gross': 'Rounds_Leading_After_Gross',
        'Leading_At_End_Of_Round_Stableford': 'Rounds_Leading_After_Stableford',
        'Lead_Gained_Count_Gross': 'Total_Lead_Gained_Gross',
        'Lead_Lost_Count_Gross': 'Total_Lead_Lost_Gross',
        'Lead_Gained_Count_Stableford': 'Total_Lead_Gained_Stableford',
        'Lead_Lost_Count_Stableford': 'Total_Lead_Lost_Stableford'
    }, inplace=True)

    # ========================================
    # 6. SCORING ACHIEVEMENTS
    # ========================================
    logger.info("Calculating scoring achievements")

    # Count hole outcomes
    scoring = all_data_df.groupby(['TEGNum', 'Pl']).apply(lambda x: pd.Series({
        'Total_Eagles': (x['GrossVP'] == -2).sum(),
        'Total_Birdies': (x['GrossVP'] == -1).sum(),
        'Total_Pars': (x['GrossVP'] == 0).sum(),
        'Total_Bogeys': (x['GrossVP'] == 1).sum(),
        'Total_Double_Bogeys': (x['GrossVP'] == 2).sum(),
        'Total_Worse_Than_Double': (x['GrossVP'] > 2).sum(),
        'Holes_In_One': (x['Sc'] == 1).sum(),
        'Total_Stableford_5s': (x['Stableford'] >= 5).sum(),
        'Total_Stableford_0s': (x['Stableford'] == 0).sum()
    }), include_groups=False).reset_index()

    # ========================================
    # 7. HISTORICAL CONTEXT
    # ========================================
    logger.info("Calculating historical rankings")

    # For historical rankings, we need to rank this TEG against all previous TEGs for the player
    # First get the earliest date for each TEG
    teg_dates = round_info_df.groupby('TEGNum')['Date'].min().reset_index()
    teg_dates.columns = ['TEGNum', 'TEG_Date']

    # Merge dates into tournament scores
    tournament_with_dates = tournament_scores.merge(teg_dates, on='TEGNum', how='left')

    # Calculate historical rankings
    historical_rankings = []

    for _, row in tournament_with_dates.iterrows():
        player = row['Pl']
        teg_num = row['TEGNum']
        teg_date = row['TEG_Date']
        gross_score = row['Tournament_Score_Gross']
        stableford_score = row['Tournament_Score_Stableford']

        # Get all TEGs for this player up to and including this date
        player_history = tournament_with_dates[
            (tournament_with_dates['Pl'] == player) &
            (tournament_with_dates['TEG_Date'] <= teg_date)
        ].copy()

        # Rank among player's TEGs
        rank_player_gross = (player_history['Tournament_Score_Gross'] < gross_score).sum() + 1
        rank_player_stableford = (player_history['Tournament_Score_Stableford'] > stableford_score).sum() + 1

        # Get all TEGs up to this date
        all_history = tournament_with_dates[tournament_with_dates['TEG_Date'] <= teg_date].copy()

        # Rank among all TEGs to date
        rank_all_gross = (all_history['Tournament_Score_Gross'] < gross_score).sum() + 1
        rank_all_stableford = (all_history['Tournament_Score_Stableford'] > stableford_score).sum() + 1

        historical_rankings.append({
            'TEGNum': teg_num,
            'Pl': player,
            'Rank_Among_Player_TEGs_Gross': rank_player_gross,
            'Rank_Among_Player_TEGs_Stableford': rank_player_stableford,
            'Rank_Among_All_TEGs_To_Date_Gross': rank_all_gross,
            'Rank_Among_All_TEGs_To_Date_Stableford': rank_all_stableford
        })

    historical_df = pd.DataFrame(historical_rankings)

    # ========================================
    # 8. MERGE ALL SECTIONS
    # ========================================
    logger.info("Merging all sections")

    summary = basic_info
    summary = summary.merge(tournament_scores, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(consistency, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(lead_tracking, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(scoring, on=['TEGNum', 'Pl'], how='left')
    summary = summary.merge(historical_df, on=['TEGNum', 'Pl'], how='left')

    # ========================================
    # 9. COLUMN ORDERING
    # ========================================
    logger.info("Ordering columns")

    column_order = [
        # Basic Info
        'TEGNum', 'Player', 'Pl', 'TEG', 'Year',

        # Tournament Scores & Rankings
        'Tournament_Score_Sc', 'Tournament_Score_Gross', 'Tournament_Score_Stableford',
        'Final_Rank_Gross', 'Final_Rank_Stableford',
        'Final_Gap_Gross', 'Final_Gap_Stableford',
        'Won_Gross', 'Won_Stableford', 'Wooden_Spoon',
        'Margin_Gross', 'Margin_Stableford',

        # Performance Consistency
        'Best_Round_Gross', 'Worst_Round_Gross', 'Range_Round_Gross', 'StdDev_Round_Gross',
        'Best_Round_Stableford', 'Worst_Round_Stableford', 'Range_Round_Stableford', 'StdDev_Round_Stableford',
        'StdDev_Hole_Gross', 'StdDev_Hole_Stableford',

        # Lead Tracking
        'Total_Holes_In_Lead_Gross', 'Total_Holes_In_Lead_Stableford',
        'Rounds_Leading_After_Gross', 'Rounds_Leading_After_Stableford',
        'Total_Lead_Gained_Gross', 'Total_Lead_Lost_Gross',
        'Total_Lead_Gained_Stableford', 'Total_Lead_Lost_Stableford',

        # Scoring Achievements
        'Total_Eagles', 'Total_Birdies', 'Total_Pars', 'Total_Bogeys',
        'Total_Double_Bogeys', 'Total_Worse_Than_Double',
        'Holes_In_One', 'Total_Stableford_5s', 'Total_Stableford_0s',

        # Historical Context
        'Rank_Among_Player_TEGs_Gross', 'Rank_Among_Player_TEGs_Stableford',
        'Rank_Among_All_TEGs_To_Date_Gross', 'Rank_Among_All_TEGs_To_Date_Stableford'
    ]

    summary = summary[column_order]

    logger.info(f"Tournament summary created: {len(summary)} rows, {len(summary.columns)} columns")

    return summary


def create_round_streaks_summary(all_data_df=None, streaks_df=None):
    """
    Create a comprehensive streaks summary for each round (unique TEG + Round + Player combination).

    This function calculates adjusted streaks for each round, showing:
    - Maximum streak lengths for each streak type within the round
    - Location information (from which hole to which hole)
    - All 10 streak types (Eagles, Birdies, Pars or Better, No +2s, No TBPs,
      No Eagles, No Birdies, Over Par, +2s or Worse, TBPs)

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data.
            If None, loads from all-data.parquet.
        streaks_df (pd.DataFrame, optional): DataFrame with streak data.
            If None, loads from streaks.parquet.

    Returns:
        pd.DataFrame: Summary table with columns:
            ['TEG', 'TEGNum', 'Round', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']
    """

    logger.info("Creating round streaks summary")

    # Import dependencies to avoid circular imports
    from teg_analysis.core.data_loader import load_all_data, read_file
    from teg_analysis.analysis.streaks import calculate_window_streaks


    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if streaks_df is None:
        streaks_df = read_file(STREAKS_PARQUET)

    # ========================================
    # 2. MERGE STREAKS WITH ROUND INFO
    # ========================================
    logger.info("Merging streaks with round information")

    # Merge to get TEG, Round, Player info
    df = streaks_df.merge(
        all_data_df[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl'],
        how='left'
    )

    # ========================================
    # 3. CALCULATE STREAKS FOR EACH ROUND
    # ========================================
    logger.info("Calculating streaks for each round")

    all_results = []

    # Get unique TEG + Round combinations
    rounds = df[['TEGNum', 'Round']].drop_duplicates().sort_values(['TEGNum', 'Round'])

    for _, row in rounds.iterrows():
        teg_num = row['TEGNum']
        round_num = row['Round']

        # Filter to this round
        round_data = df[(df['TEGNum'] == teg_num) & (df['Round'] == round_num)].copy()

        if len(round_data) == 0:
            continue

        # Sort by Career Count for correct streak calculation
        round_data = round_data.sort_values(['Pl', 'Career Count'])

        # Keep player mapping for later
        player_mapping = round_data[['Player', 'Pl']].drop_duplicates()

        # Calculate window streaks for this round
        round_streaks = calculate_window_streaks(round_data)

        # Merge player codes back
        round_streaks = round_streaks.merge(player_mapping, on='Player', how='left')

        # Add TEG and Round info
        round_streaks['TEGNum'] = teg_num
        round_streaks['Round'] = round_num

        all_results.append(round_streaks)

    # ========================================
    # 4. COMBINE AND FORMAT
    # ========================================
    if len(all_results) == 0:
        logger.warning("No round streaks calculated")
        return pd.DataFrame()

    final_df = pd.concat(all_results, ignore_index=True)

    # Add TEG name
    teg_mapping = all_data_df[['TEGNum', 'TEG']].drop_duplicates().set_index('TEGNum')['TEG'].to_dict()
    final_df['TEG'] = final_df['TEGNum'].map(teg_mapping)

    # Rename columns with underscores for consistency
    final_df = final_df.rename(columns={
        'Streak Type': 'Streak_Type',
        'Max Streak': 'Max_Streak'
    })

    # Reorder columns
    final_df = final_df[['TEG', 'TEGNum', 'Round', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']]

    # Sort by TEG, Round, Player, Streak Type
    final_df = final_df.sort_values(['TEGNum', 'Round', 'Player', 'Streak_Type']).reset_index(drop=True)

    logger.info(f"Round streaks summary created: {len(final_df)} rows")

    return final_df


def create_tournament_streaks_summary(all_data_df=None, streaks_df=None):
    """
    Create a comprehensive streaks summary for each tournament (unique TEG + Player combination).

    This function calculates adjusted streaks for each tournament, showing:
    - Maximum streak lengths for each streak type within the tournament
    - Location information (from which hole to which hole)
    - All 10 streak types (Eagles, Birdies, Pars or Better, No +2s, No TBPs,
      No Eagles, No Birdies, Over Par, +2s or Worse, TBPs)

    Args:
        all_data_df (pd.DataFrame, optional): DataFrame with hole-by-hole data.
            If None, loads from all-data.parquet.
        streaks_df (pd.DataFrame, optional): DataFrame with streak data.
            If None, loads from streaks.parquet.

    Returns:
        pd.DataFrame: Summary table with columns:
            ['TEG', 'TEGNum', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']
    """

    logger.info("Creating tournament streaks summary")

    # Import dependencies to avoid circular imports
    from teg_analysis.core.data_loader import load_all_data, read_file
    from teg_analysis.analysis.streaks import calculate_window_streaks


    # ========================================
    # 1. LOAD DATA
    # ========================================
    if all_data_df is None:
        all_data_df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

    if streaks_df is None:
        streaks_df = read_file(STREAKS_PARQUET)

    # ========================================
    # 2. MERGE STREAKS WITH TEG INFO
    # ========================================
    logger.info("Merging streaks with TEG information")

    # Merge to get TEG, Player info
    df = streaks_df.merge(
        all_data_df[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl'],
        how='left'
    )

    # ========================================
    # 3. CALCULATE STREAKS FOR EACH TEG
    # ========================================
    logger.info("Calculating streaks for each tournament")

    all_results = []

    # Get unique TEGs
    tegs = df['TEGNum'].unique()

    for teg_num in sorted(tegs):
        # Filter to this TEG
        teg_data = df[df['TEGNum'] == teg_num].copy()

        if len(teg_data) == 0:
            continue

        # Sort by Career Count for correct streak calculation
        teg_data = teg_data.sort_values(['Pl', 'Career Count'])

        # Keep player mapping for later
        player_mapping = teg_data[['Player', 'Pl']].drop_duplicates()

        # Calculate window streaks for this TEG
        teg_streaks = calculate_window_streaks(teg_data)

        # Merge player codes back
        teg_streaks = teg_streaks.merge(player_mapping, on='Player', how='left')

        # Add TEG info
        teg_streaks['TEGNum'] = teg_num

        all_results.append(teg_streaks)

    # ========================================
    # 4. COMBINE AND FORMAT
    # ========================================
    if len(all_results) == 0:
        logger.warning("No tournament streaks calculated")
        return pd.DataFrame()

    final_df = pd.concat(all_results, ignore_index=True)

    # Add TEG name
    teg_mapping = all_data_df[['TEGNum', 'TEG']].drop_duplicates().set_index('TEGNum')['TEG'].to_dict()
    final_df['TEG'] = final_df['TEGNum'].map(teg_mapping)

    # Rename columns with underscores for consistency
    final_df = final_df.rename(columns={
        'Streak Type': 'Streak_Type',
        'Max Streak': 'Max_Streak'
    })

    # Reorder columns
    final_df = final_df[['TEG', 'TEGNum', 'Player', 'Pl', 'Streak_Type', 'Max_Streak', 'Location']]

    # Sort by TEG, Player, Streak Type
    final_df = final_df.sort_values(['TEGNum', 'Player', 'Streak_Type']).reset_index(drop=True)

    logger.info(f"Tournament streaks summary created: {len(final_df)} rows")

    return final_df


