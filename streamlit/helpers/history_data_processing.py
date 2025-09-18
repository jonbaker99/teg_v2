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


def get_eagles_data(all_data):
    """
    Find all Eagles (-2 gross vs par) scored in TEG history.
    
    Args:
        all_data (pd.DataFrame): Complete scoring data with Par, Score, Player, TEG, Round, Hole columns
        
    Returns:
        pd.DataFrame: Eagles data with Player, Date, Course, Hole columns
        
    Purpose:
        Identifies all Eagles (score 2 under par) for honours board display
    """
    # Find all Eagles: Gross score is 2 under par
    eagles = all_data[all_data['GrossVP'] == -2.0].copy()
    
    if eagles.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])
    
    # Create formatted hole information as "TEG X | Rd X | Hole X"
    eagles['Hole'] = eagles['TEG'].astype(str) + ' | Rd ' + eagles['Round'].astype(str) + ' | Hole ' + eagles['Hole'].astype(str)
    
    # Select and order columns for display
    eagles_display = eagles[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()
    
    # Sort by TEG, Round, Hole (using original numeric values)
    eagles_display = eagles_display.sort_values(['TEGNum', 'Date'])
    
    # Remove TEGNum from final display
    eagles_display = eagles_display[['Player', 'Date', 'Course', 'Hole']]
    
    return eagles_display


def get_holes_in_one_data(all_data):
    """
    Find all Holes in One scored in TEG history.
    
    Args:
        all_data (pd.DataFrame): Complete scoring data with Score, Player, TEG, Round, Hole columns
        
    Returns:
        pd.DataFrame: Holes in One data with Player, Date, Course, Hole columns
        
    Purpose:
        Identifies all Holes in One (score of 1) for honours board display
    """
    # Find all Holes in One: Gross score is 1
    holes_in_one = all_data[all_data['Sc'] == 1.0].copy()
    
    if holes_in_one.empty:
        return pd.DataFrame(columns=['Player', 'Date', 'Course', 'Hole'])
    
    # Create formatted hole information as "TEG X | Rd X | Hole X"
    holes_in_one['Hole'] = holes_in_one['TEG'].astype(str) + ' | Rd ' + holes_in_one['Round'].astype(str) + ' | Hole ' + holes_in_one['Hole'].astype(str)
    
    # Select and order columns for display
    holes_in_one_display = holes_in_one[['Player', 'Date', 'Course', 'Hole', 'TEGNum']].copy()
    
    # Sort by TEG, Round, Hole (using original numeric values)
    holes_in_one_display = holes_in_one_display.sort_values(['TEGNum', 'Date'])
    
    # Remove TEGNum from final display
    holes_in_one_display = holes_in_one_display[['Player', 'Date', 'Course', 'Hole']]
    
    return holes_in_one_display


def get_incomplete_tegs():
    """
    Find TEGs that are in progress (have some data but incomplete rounds).
    
    Returns:
        pd.DataFrame: Incomplete TEG data with TEG, Year, Area columns
        
    Purpose:
        Identifies TEGs that have started but not finished for history display
    """
    from utils import load_all_data, read_file, ROUND_INFO_CSV, exclude_incomplete_tegs_function
    
    # Load all data including incomplete TEGs
    all_data_with_incomplete = load_all_data(exclude_incomplete_tegs=False)
    
    # Load only complete data 
    complete_data = load_all_data(exclude_incomplete_tegs=True)
    
    # Find TEGs that exist in all data but not in complete data
    all_tegs = set(all_data_with_incomplete['TEGNum'].unique())
    complete_tegs = set(complete_data['TEGNum'].unique())
    incomplete_teg_nums = all_tegs - complete_tegs
    
    if not incomplete_teg_nums:
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])
    
    # Get metadata for incomplete TEGs from round_info
    round_info = read_file(ROUND_INFO_CSV)
    incomplete_tegs = round_info[round_info['TEGNum'].isin(incomplete_teg_nums)]
    
    # Get unique TEG entries (one row per TEG) - keep TEGNum for sorting
    incomplete_summary = incomplete_tegs[['TEGNum', 'TEG', 'Year', 'Area']].drop_duplicates()
    
    # Sort by TEGNum then drop it since we only need TEG, Year, Area for output
    incomplete_summary = incomplete_summary.sort_values('TEGNum')[['TEG', 'Year', 'Area']]
    
    return incomplete_summary


def get_future_tegs():
    """
    Load planned future TEGs that haven't started yet.
    
    Returns:
        pd.DataFrame: Future TEG data with TEG, Year, Area columns
        
    Purpose:
        Gets TEGs that are planned but haven't started for history display
    """
    from utils import read_file
    
    try:
        # Try to load future TEGs from a dedicated file
        future_tegs = read_file('data/future_tegs.csv')
        # Convert Year column to integers to avoid decimal display
        future_tegs['Year'] = future_tegs['Year'].astype(int)
        return future_tegs[['TEG', 'Year', 'Area']].sort_values('Year')
    except Exception:
        # If no future TEGs file exists, return empty DataFrame
        return pd.DataFrame(columns=['TEG', 'Year', 'Area'])


def prepare_complete_history_table(winners_df):
    """
    Prepare complete history table including completed, incomplete, and future TEGs.
    
    Args:
        winners_df (pd.DataFrame): Winners data from completed TEGs only
        
    Returns:
        pd.DataFrame: Complete history table with TBC entries for incomplete/future TEGs
        
    Purpose:
        Creates comprehensive history view showing all TEGs regardless of completion status
    """
    # Start with completed TEGs history
    completed_history = prepare_history_table_display(winners_df)
    
    # Get incomplete TEGs
    incomplete_tegs = get_incomplete_tegs()
    
    # Get future TEGs  
    future_tegs = get_future_tegs()
    
    # Get all TEG names that already exist in completed or incomplete data
    existing_tegs = set()
    
    # Add completed TEG names (extract from "TEG X (YYYY)" format)
    import re
    for teg_str in completed_history['TEG']:
        match = re.search(r'(TEG \d+)', teg_str)
        if match:
            existing_tegs.add(match.group(1))
    
    # Add incomplete TEG names
    if not incomplete_tegs.empty:
        existing_tegs.update(incomplete_tegs['TEG'].tolist())
    
    # Filter out future TEGs that already exist in the data
    if not future_tegs.empty:
        future_tegs = future_tegs[~future_tegs['TEG'].isin(existing_tegs)]
    
    # Combine incomplete and future TEGs (after filtering duplicates)
    pending_tegs = pd.concat([incomplete_tegs, future_tegs], ignore_index=True)
    
    if pending_tegs.empty:
        return completed_history
    
    # Create TBC entries for pending TEGs
    tbc_entries = []
    for _, row in pending_tegs.iterrows():
        tbc_entry = {
            'TEG': f"{row['TEG']} ({row['Year']})",
            'Area': row['Area'],
            'TEG Trophy': 'TBC',
            'Green Jacket': 'TBC', 
            'HMM Wooden Spoon': 'TBC'
        }
        tbc_entries.append(tbc_entry)
    
    # Convert to DataFrame
    tbc_df = pd.DataFrame(tbc_entries)
    
    # Combine completed and TBC entries
    complete_history = pd.concat([completed_history, tbc_df], ignore_index=True)
    
    # Sort by TEG number (extract from TEG name)
    def extract_teg_num(teg_str):
        try:
            # Extract number from "TEG X (YYYY)" format
            import re
            match = re.search(r'TEG (\d+)', teg_str)
            return int(match.group(1)) if match else 999
        except:
            return 999
    
    complete_history['_sort_order'] = complete_history['TEG'].apply(extract_teg_num)
    complete_history = complete_history.sort_values('_sort_order').drop('_sort_order', axis=1)

    return complete_history


# ============================================
#  TEG COMPLETENESS CHECKING FUNCTIONS
# ============================================

def check_winner_completeness():
    """
    Check if cached winners match completed TEGs status.

    Returns:
        set: Set of TEG numbers that are completed but missing from winners cache
    """
    from utils import read_file

    try:
        # Load status files
        completed_tegs = read_file('data/completed_tegs.csv')
        cached_winners = read_file('data/teg_winners.csv')

        # Extract TEG numbers from both sources
        completed_teg_nums = set(completed_tegs['TEGNum']) if not completed_tegs.empty else set()

        # Extract TEG numbers from cached winners (from TEG column like "TEG 18")
        cached_teg_nums = set()
        if not cached_winners.empty:
            import re
            for teg_str in cached_winners['TEG']:
                match = re.search(r'TEG (\d+)', str(teg_str))
                if match:
                    cached_teg_nums.add(int(match.group(1)))

        # Identify missing winners
        missing_winners = completed_teg_nums - cached_teg_nums

        return missing_winners

    except Exception as e:
        print(f"Error checking winner completeness: {e}")
        return set()


def display_completeness_status():
    """
    Show status if winners are missing for completed TEGs.
    """
    import streamlit as st

    missing = check_winner_completeness()
    if missing:
        st.warning(f"Winners missing for completed TEGs: {sorted(missing)}")

        # Offer to calculate and save winners for missing TEGs
        if st.button("Calculate and Save Winners for Missing TEGs"):
            with st.spinner("Calculating winners for completed TEGs..."):
                calculate_and_save_missing_winners(missing)
            st.success("Winners updated! Refreshing page...")
            st.rerun()

        st.info("Or run the data update process to refresh all winner information.")


def calculate_and_save_missing_winners(missing_teg_nums):
    """
    Calculate and save winners for specific missing TEGs.

    Args:
        missing_teg_nums: Set of TEG numbers to calculate winners for
    """
    import streamlit as st
    import pandas as pd
    from utils import load_all_data, read_file, write_file

    # Load all data (expensive operation)
    all_data = load_all_data()

    if all_data.empty:
        st.error("No data available to calculate winners")
        return

    # Load existing cached winners
    try:
        cached_winners = read_file('data/teg_winners.csv')
    except Exception:
        # Create empty DataFrame with correct structure
        cached_winners = pd.DataFrame(columns=['TEG', 'Year', 'Area', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'])

    # Calculate winners only for missing TEGs
    new_winners = []
    for teg_num in missing_teg_nums:
        try:
            # Get TEG data
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if teg_data.empty:
                st.warning(f"No data found for TEG {teg_num}")
                continue

            # Get TEG info from data
            teg_info = teg_data.iloc[0]
            teg_name = teg_info['TEG']
            year = teg_info['Year']
            area = teg_info['Area'] if 'Area' in teg_info else "Unknown"

            # Calculate winners using existing logic
            from utils import get_teg_winners
            winners_df = get_teg_winners(teg_data)

            if not winners_df.empty:
                # Get the row for this specific TEG
                teg_winners = winners_df[winners_df['TEG'] == teg_name]
                if not teg_winners.empty:
                    winner_row = teg_winners.iloc[0]
                    new_winner_row = {
                        'TEG': teg_name,
                        'Year': year,
                        'Area': area,
                        'TEG Trophy': winner_row.get('TEG Trophy', 'Unknown'),
                        'Green Jacket': winner_row.get('Green Jacket', 'Unknown'),
                        'HMM Wooden Spoon': winner_row.get('HMM Wooden Spoon', 'Unknown')
                    }
                    new_winners.append(new_winner_row)

        except Exception as e:
            st.error(f"Error calculating winners for TEG {teg_num}: {e}")

    if new_winners:
        # Add new winners to cached data
        new_winners_df = pd.DataFrame(new_winners)
        updated_winners = pd.concat([cached_winners, new_winners_df], ignore_index=True)

        # Sort by Year to maintain order
        updated_winners = updated_winners.sort_values('Year')

        # Save updated winners
        write_file('data/teg_winners.csv', updated_winners)

        # Clear relevant caches after update
        st.cache_data.clear()

        st.success(f"Added winners for {len(new_winners)} TEGs to cache")
    else:
        st.warning("No winners could be calculated for the missing TEGs")


def load_cached_winners():
    """
    Load cached winners from teg_winners.csv file and calculate any missing ones.

    Returns:
        tuple: (winners_data, missing_teg_nums) or (None, set()) if no cached file
    """
    import pandas as pd
    from utils import read_file, load_all_data, get_teg_winners

    try:
        # Try to load cached winners
        cached_winners = read_file('data/teg_winners.csv')

        # Check for missing winners using existing function
        missing = check_winner_completeness()

        # If no missing winners, return cached data as before
        if not missing:
            cached_winners["TEG"] = (
                cached_winners['TEG'].astype(str) + " (" +
                cached_winners['Year'].astype(str) + ")"
            )
            cached_winners = cached_winners.drop(columns=['Year'])
            return cached_winners, set()

        # Calculate missing winners and append to display
        all_data = load_all_data()
        for teg_num in missing:
            try:
                teg_data = all_data[all_data['TEGNum'] == teg_num]
                if not teg_data.empty:
                    winners_df = get_teg_winners(teg_data)
                    if not winners_df.empty:
                        # Get winner info for this TEG
                        teg_info = teg_data.iloc[0]
                        winner_row = winners_df.iloc[0]
                        new_row = {
                            'TEG': teg_info['TEG'],
                            'Year': teg_info['Year'],
                            'Area': teg_info['Area'],
                            'TEG Trophy': winner_row.get('TEG Trophy', 'Unknown'),
                            'Green Jacket': winner_row.get('Green Jacket', 'Unknown'),
                            'HMM Wooden Spoon': winner_row.get('HMM Wooden Spoon', 'Unknown')
                        }
                        cached_winners = pd.concat([cached_winners, pd.DataFrame([new_row])], ignore_index=True)
            except Exception as e:
                print(f"Error calculating winners for TEG {teg_num}: {e}")

        # Format for display consistency
        cached_winners["TEG"] = (
            cached_winners['TEG'].astype(str) + " (" +
            cached_winners['Year'].astype(str) + ")"
        )
        cached_winners = cached_winners.drop(columns=['Year'])

        return cached_winners, missing

    except Exception as e:
        # If cached file doesn't exist or has issues, return None
        print(f"Could not load cached winners: {e}")
        return None, set()


def prepare_complete_history_table_fast(cached_winners_df=None):
    """
    Prepare complete history table using cached winners data when available.

    Args:
        cached_winners_df (pd.DataFrame, optional): Pre-loaded cached winners data

    Returns:
        pd.DataFrame: Complete history table with TBC entries for incomplete/future TEGs

    Purpose:
        Fast version of prepare_complete_history_table that uses cached data
    """

    # Try to use provided cached data, or load it
    if cached_winners_df is None:
        cached_winners_df = load_cached_winners()

    # If no cached data available, fall back to calculation
    if cached_winners_df is None:
        print("No cached winners data available, falling back to calculation...")
        from utils import load_all_data, get_teg_winners
        all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)
        winners_with_year = get_teg_winners(all_data)
        completed_history = prepare_history_table_display(winners_with_year)
    else:
        completed_history = cached_winners_df.copy()

    # Get future TEGs
    future_tegs = get_future_tegs()

    # Get all TEG names that already exist in completed data
    existing_tegs = set()

    # Add completed TEG names (extract from "TEG X (YYYY)" format)
    import re
    for teg_str in completed_history['TEG']:
        match = re.search(r'(TEG \d+)', teg_str)
        if match:
            existing_tegs.add(match.group(1))

    # Filter out future TEGs that already exist in the data
    if not future_tegs.empty:
        future_tegs = future_tegs[~future_tegs['TEG'].isin(existing_tegs)]

    if future_tegs.empty:
        return completed_history

    # Create TBC entries for future TEGs
    tbc_entries = []
    for _, row in future_tegs.iterrows():
        tbc_entry = {
            'TEG': f"{row['TEG']} ({row['Year']})",
            'Area': row['Area'],
            'TEG Trophy': 'TBC',
            'Green Jacket': 'TBC',
            'HMM Wooden Spoon': 'TBC'
        }
        tbc_entries.append(tbc_entry)

    # Convert to DataFrame
    tbc_df = pd.DataFrame(tbc_entries)

    # Combine completed and TBC entries
    complete_history = pd.concat([completed_history, tbc_df], ignore_index=True)

    # Sort by TEG number (extract from TEG name)
    def extract_teg_num(teg_str):
        try:
            # Extract number from "TEG X (YYYY)" format
            import re
            match = re.search(r'TEG (\d+)', teg_str)
            return int(match.group(1)) if match else 999
        except:
            return 999

    complete_history['_sort_order'] = complete_history['TEG'].apply(extract_teg_num)
    complete_history = complete_history.sort_values('_sort_order').drop('_sort_order', axis=1)

    return complete_history


# ============================================
#  TEG COMPLETENESS CHECKING FUNCTIONS
# ============================================

def check_winner_completeness():
    """
    Check if cached winners match completed TEGs status.

    Returns:
        set: Set of TEG numbers that are completed but missing from winners cache
    """
    from utils import read_file

    try:
        # Load status files
        completed_tegs = read_file('data/completed_tegs.csv')
        cached_winners = read_file('data/teg_winners.csv')

        # Extract TEG numbers from both sources
        completed_teg_nums = set(completed_tegs['TEGNum']) if not completed_tegs.empty else set()

        # Extract TEG numbers from cached winners (from TEG column like "TEG 18")
        cached_teg_nums = set()
        if not cached_winners.empty:
            import re
            for teg_str in cached_winners['TEG']:
                match = re.search(r'TEG (\d+)', str(teg_str))
                if match:
                    cached_teg_nums.add(int(match.group(1)))

        # Identify missing winners
        missing_winners = completed_teg_nums - cached_teg_nums

        return missing_winners

    except Exception as e:
        print(f"Error checking winner completeness: {e}")
        return set()


def display_completeness_status():
    """
    Show status if winners are missing for completed TEGs.
    """
    import streamlit as st

    missing = check_winner_completeness()
    if missing:
        st.warning(f"Winners missing for completed TEGs: {sorted(missing)}")

        # Offer to calculate and save winners for missing TEGs
        if st.button("Calculate and Save Winners for Missing TEGs"):
            with st.spinner("Calculating winners for completed TEGs..."):
                calculate_and_save_missing_winners(missing)
            st.success("Winners updated! Refreshing page...")
            st.rerun()

        st.info("Or run the data update process to refresh all winner information.")


def calculate_and_save_missing_winners(missing_teg_nums):
    """
    Calculate and save winners for specific missing TEGs.

    Args:
        missing_teg_nums: Set of TEG numbers to calculate winners for
    """
    import streamlit as st
    import pandas as pd
    from utils import load_all_data, read_file, write_file

    # Load all data (expensive operation)
    all_data = load_all_data()

    if all_data.empty:
        st.error("No data available to calculate winners")
        return

    # Load existing cached winners
    try:
        cached_winners = read_file('data/teg_winners.csv')
    except Exception:
        # Create empty DataFrame with correct structure
        cached_winners = pd.DataFrame(columns=['TEG', 'Year', 'Area', 'TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'])

    # Calculate winners only for missing TEGs
    new_winners = []
    for teg_num in missing_teg_nums:
        try:
            # Get TEG data
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if teg_data.empty:
                st.warning(f"No data found for TEG {teg_num}")
                continue

            # Get TEG info from data
            teg_info = teg_data.iloc[0]
            teg_name = teg_info['TEG']
            year = teg_info['Year']
            area = teg_info['Area'] if 'Area' in teg_info else "Unknown"

            # Calculate winners using existing logic
            from utils import get_teg_winners
            winners_df = get_teg_winners(teg_data)

            if not winners_df.empty:
                # Get the row for this specific TEG
                teg_winners = winners_df[winners_df['TEG'] == teg_name]
                if not teg_winners.empty:
                    winner_row = teg_winners.iloc[0]
                    new_winner_row = {
                        'TEG': teg_name,
                        'Year': year,
                        'Area': area,
                        'TEG Trophy': winner_row.get('TEG Trophy', 'Unknown'),
                        'Green Jacket': winner_row.get('Green Jacket', 'Unknown'),
                        'HMM Wooden Spoon': winner_row.get('HMM Wooden Spoon', 'Unknown')
                    }
                    new_winners.append(new_winner_row)

        except Exception as e:
            st.error(f"Error calculating winners for TEG {teg_num}: {e}")

    if new_winners:
        # Add new winners to cached data
        new_winners_df = pd.DataFrame(new_winners)
        updated_winners = pd.concat([cached_winners, new_winners_df], ignore_index=True)

        # Sort by Year to maintain order
        updated_winners = updated_winners.sort_values('Year')

        # Save updated winners
        write_file('data/teg_winners.csv', updated_winners)

        # Clear relevant caches after update
        st.cache_data.clear()

        st.success(f"Added winners for {len(new_winners)} TEGs to cache")
    else:
        st.warning("No winners could be calculated for the missing TEGs")