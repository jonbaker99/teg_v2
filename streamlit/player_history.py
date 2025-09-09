# === IMPORTS ===
import streamlit as st
import pandas as pd
import logging
import re

# Import data loading functions from main utils
from utils import get_complete_teg_data, load_datawrapper_css, datawrapper_table

# === CONFIGURATION ===
st.title("Player Rankings by TEG")

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === POST-PROCESSING FUNCTION ===

def post_process_ranking_table(df: pd.DataFrame, player_col="Player") -> str:
    d = df.copy()
    if player_col not in d.columns:
        player_col = d.columns[0]
    d.index.name = None
    d.columns.name = None

    classes = pd.DataFrame("", index=d.index, columns=d.columns)
    rank_pat = re.compile(r"^\d+=?$")

    for c in [c for c in d.columns if c != player_col]:
        s = d[c].astype("string")  # 🔹 keep <NA> for missing values

        # First place
        classes.loc[s.isin(["1", "1="]), c] += " first-place"

        # 🔹 Last place: only consider real ranks ("N" or "N="), ignore everything else
        mask_rank = s.str.fullmatch(rank_pat)
        numeric_part = s.where(mask_rank).str.replace("=", "", regex=False)
        num = pd.to_numeric(numeric_part, errors="coerce").astype("Int64")

        if num.notna().any():
            max_rank = int(num.max())
            mask_last = s.isin([str(max_rank), f"{max_rank}="])
            classes.loc[mask_last, c] += " last-place"

    # 🔹 Formatter: show "-" for NaN, wrap rank text in <span> for the shape layering
    def fmt(val):
        if pd.isna(val):
            return "-"                 # display only; data stays NaN
        s = str(val)
        return f'<span>{s}</span>' if rank_pat.match(s) else s

    styler = (
        d.style
         .hide(axis="index")
         .format(fmt, escape=None)   # allow the <span>
         .set_td_classes(classes)
         .set_table_attributes('class="datawrapper-table player-ranking-table"')
    )
    return styler.to_html()

def create_position_count_summary(ranked_df: pd.DataFrame, player_col="Player") -> pd.DataFrame:
    """
    Create summary showing count of each finishing position for each player.
    
    Args:
        ranked_df: DataFrame with players as rows, TEGs as columns, ranks as values
        player_col: Name of the player column
        
    Returns:
        DataFrame with position counts (1st, 2nd, 3rd, etc., Not Played)
    """
    # Get all rank columns (exclude player column)
    rank_columns = [col for col in ranked_df.columns if col != player_col]
    
    # Initialize results dataframe
    summary_data = []
    
    for _, row in ranked_df.iterrows():
        player_name = row[player_col]
        positions = row[rank_columns]
        
        # Count occurrences of each position
        position_counts = {}
        
        # Count not played (NaN values)
        not_played = positions.isna().sum()
        
        # Count each ranking position
        played_positions = positions.dropna().astype(str)
        for pos in played_positions:
            # Remove '=' from tied positions for counting
            clean_pos = pos.replace('=', '')
            if clean_pos.isdigit():
                pos_key = f"{clean_pos}"
                position_counts[pos_key] = position_counts.get(pos_key, 0) + 1
        
        # Create row for this player
        row_data = {'Player': player_name}
        
        # Add position counts (1 through max position found)
        if position_counts:
            max_pos = max(int(k) for k in position_counts.keys())
            for i in range(1, max_pos + 1):
                row_data[f"{i}"] = position_counts.get(str(i), 0)
        
        row_data['Not Played'] = not_played
        summary_data.append(row_data)
    
    # Convert to DataFrame and fill missing position columns with 0
    summary_df = pd.DataFrame(summary_data)
    
    # Ensure all position columns exist and are in order
    position_cols = [col for col in summary_df.columns if col.isdigit()]
    if position_cols:
        max_position = max(int(col) for col in position_cols)
        for i in range(1, max_position + 1):
            if str(i) not in summary_df.columns:
                summary_df[str(i)] = 0
    
    # Reorder columns: Player, then positions 1-N, then Not Played
    position_cols = sorted([col for col in summary_df.columns if col.isdigit()], key=int)
    column_order = ['Player'] + position_cols + ['Not Played']
    summary_df = summary_df[column_order].fillna(0)
    
    # Convert position counts to integers
    for col in column_order[1:]:  # Skip Player column
        summary_df[col] = summary_df[col].astype(int)
    
    return summary_df


def create_average_position_summary(ranked_df: pd.DataFrame, player_col="Player") -> pd.DataFrame:
    """
    Create summary showing average finishing position for each player.
    
    Args:
        ranked_df: DataFrame with players as rows, TEGs as columns, ranks as values
        player_col: Name of the player column
        
    Returns:
        DataFrame with average positions, sorted by best average
    """
    # Get all rank columns (exclude player column)  
    rank_columns = [col for col in ranked_df.columns if col != player_col]
    
    summary_data = []
    
    for _, row in ranked_df.iterrows():
        player_name = row[player_col]
        positions = row[rank_columns]
        
        # Get numeric positions (exclude NaN and remove '=' from ties)
        numeric_positions = []
        for pos in positions.dropna():
            clean_pos = str(pos).replace('=', '')
            if clean_pos.isdigit():
                numeric_positions.append(int(clean_pos))
        
        # Calculate average if player has played
        if numeric_positions:
            avg_position = sum(numeric_positions) / len(numeric_positions)
            tegs_played = len(numeric_positions)
        else:
            avg_position = None
            tegs_played = 0
        
        summary_data.append({
            'Player': player_name,
            'TEGs Played': tegs_played,
            'Average Position': avg_position
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by average position (best first), with non-players at bottom
    summary_df = summary_df.sort_values(['TEGs Played', 'Average Position'], 
                                       ascending=[False, True])
    
    # Format average position to 2 decimal places
    summary_df['Average Position'] = summary_df['Average Position'].round(2)
    
    return summary_df

def create_combined_position_summary(ranked_df: pd.DataFrame, player_col="Player") -> pd.DataFrame:
    """
    Create combined summary table with average position and position counts.
    
    Args:
        ranked_df: DataFrame with players as rows, TEGs as columns, ranks as values
        player_col: Name of the player column
        
    Returns:
        DataFrame with Player, Average, Played, and position counts (1st-6th)
    """
    # Get all rank columns (exclude player column)
    rank_columns = [col for col in ranked_df.columns if col != player_col]
    
    summary_data = []
    
    for _, row in ranked_df.iterrows():
        player_name = row[player_col]
        positions = row[rank_columns]
        
        # Get numeric positions (exclude NaN and remove '=' from ties)
        numeric_positions = []
        position_counts = {str(i): 0 for i in range(1, 7)}  # Initialize 1st-6th
        
        for pos in positions.dropna():
            clean_pos = str(pos).replace('=', '')
            if clean_pos.isdigit():
                numeric_positions.append(int(clean_pos))
                # Count positions 1-6 only
                if 1 <= int(clean_pos) <= 6:
                    position_counts[clean_pos] += 1
        
        # Calculate average if player has played
        if numeric_positions:
            avg_position = sum(numeric_positions) / len(numeric_positions)
            tegs_played = len(numeric_positions)
        else:
            avg_position = float('inf')  # Will sort to bottom
            tegs_played = 0
        
        # Create row data
        row_data = {
            '': player_name,
            'Ave': round(avg_position, 1) if avg_position != float('inf') else None,
            'TEGs': tegs_played,
            '1st': position_counts['1'],
            '2nd': position_counts['2'], 
            '3rd': position_counts['3'],
            '4th': position_counts['4'],
            '5th': position_counts['5'],
            '6th': position_counts['6']
        }
        
        summary_data.append(row_data)
    
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by average position (best first), players who haven't played go to bottom
    summary_df = summary_df.sort_values('Ave', ascending=True, na_position='last')
    
    return summary_df

# === CORE RANKING FUNCTION ===
@st.cache_data
def create_teg_ranking_table(teg_data: pd.DataFrame, 
                           scoring_type: str, 
                           row_dimension: str = 'Player', 
                           col_dimension: str = 'TEG') -> pd.DataFrame:
    """
    Create ranking table for completed TEGs by scoring type.
    
    Parameters:
    - teg_data: DataFrame from get_complete_teg_data() or similar
    - scoring_type: 'Sc', 'GrossVP', 'NetVP', 'Stableford'  
    - row_dimension: 'Player', 'Pl' (for bonus feature)
    - col_dimension: 'TEG', 'TEGNum' (for bonus feature)
    
    Returns:
    - DataFrame with Players as rows, TEGs as columns, ranks as values
    """
    logger.info(f"Creating TEG ranking table for {scoring_type}")
    
    # Step 1: Create pivot table with totals by scoring type
    pivot_df = teg_data.pivot_table(
        index=row_dimension, 
        columns=col_dimension, 
        values=scoring_type, 
        aggfunc='sum',  # Sum scores across all rounds in each TEG
        fill_value=None  # Use None for TEGs where player didn't participate
    )
    
    # Step 1.5: Sort columns properly (TEG 1, TEG 2, ... not TEG 1, TEG 10, TEG 11, TEG 2...)
    if col_dimension == 'TEG':
        # Sort by extracting the numeric part from "TEG X" format
        def teg_sort_key(teg_name):
            try:
                return int(str(teg_name).replace('TEG ', ''))
            except (ValueError, AttributeError):
                return 999  # Put any non-standard names at the end
        
        sorted_columns = sorted(pivot_df.columns, key=teg_sort_key)
        pivot_df = pivot_df[sorted_columns]
        
    elif col_dimension == 'TEGNum':
        # Sort by TEGNum values directly (should be numeric)
        sorted_columns = sorted(pivot_df.columns)
        pivot_df = pivot_df[sorted_columns]
    
    # Step 2: Apply ranking logic (reuse existing ascending/descending logic)
    # Determine ranking order based on scoring type
    ascending = True  # Default for gross scores (lower is better)
    if scoring_type == 'Stableford':
        ascending = False  # Higher stableford is better
    
    # Step 3: Rank each TEG column independently
    ranked_df = pivot_df.copy()

    for teg_col in pivot_df.columns:
        col_data = pivot_df[teg_col].dropna()
        if len(col_data) == 0:
            continue

        # Compute ranks (min method keeps shared lowest rank for ties)
        ranks = col_data.rank(method='min', ascending=ascending)

        # Convert all ranks to integer strings
        ranks = ranks.astype(int).astype(str)

        # Mark ties with '='
        is_tie = col_data.duplicated(keep=False)
        if is_tie.any():
            ranks.loc[is_tie] = ranks.loc[is_tie] + '='

        # Write back
        ranked_df.loc[ranks.index, teg_col] = ranks
    
    # Step 4: Clean up the output
    ranked_df = ranked_df.reset_index()
    
    # Sort by player name for consistent display
    ranked_df = ranked_df.sort_values(by=row_dimension)
    
    logger.info(f"TEG ranking table created with {len(ranked_df)} players and {len(ranked_df.columns)-1} TEGs")
    
    return ranked_df

# === USER INTERFACE ===
# st.markdown("Select a scoring type to see how each player ranked in each completed TEG.")
# st.markdown("**Note**: Only completed TEGs are included. Empty cells indicate the player did not participate in that TEG.")

scoring_options = {
    # 'Gross Score': 'Sc',
    'Stableford Points': 'Stableford',
    'Gross vs Par': 'GrossVP', 
    'Net vs Par': 'NetVP'
}

# Create tabs using the scoring options
tabs = st.tabs(list(scoring_options.keys()))

# Load data once outside the tabs
with st.spinner("Loading TEG data..."):
    teg_data = get_complete_teg_data()

# Bonus feature: Row/Column selection
# st.markdown("---")
with st.expander("Advanced Options"):
    col1, col2 = st.columns(2)
    
    with col1:
        row_options = {'Full Name': 'Player', 'Initials': 'Pl'}
        selected_row = st.selectbox(
            "Rows (Players):",
            options=list(row_options.keys()),
            index=1
        )
        row_dimension = row_options[selected_row]
    
    with col2:
        col_options = {'TEG Name': 'TEG', 'TEG Number': 'TEGNum'}
        selected_col = st.selectbox(
            "Columns (TEGs):",
            options=list(col_options.keys()), 
            index=1
        )
        col_dimension = col_options[selected_col]

st.markdown("---")

# === DATA PROCESSING AND DISPLAY ===

# Iterate through each tab
for i, (friendly_name, scoring_type) in enumerate(scoring_options.items()):
    with tabs[i]:
        with st.spinner(f"Calculating {friendly_name} rankings..."):
            # Create the ranking table for this scoring type
            ranking_table = create_teg_ranking_table(
                teg_data=teg_data,
                scoring_type=scoring_type,
                row_dimension=row_dimension,
                col_dimension=col_dimension
            )

        # Display title and explanation
        st.markdown(f"**{friendly_name} Rankings by TEG**")
        # st.caption("Numbers show rank within that TEG. Ties are marked with '='. Empty cells = did not participate.")

       # Format the table for display
        if not ranking_table.empty:
            display_table = (
                ranking_table
                    .reset_index(drop=True)   # drop the numeric index column
            )
            display_table.index.name = None   
            display_table.columns.name = None # remove the 'TEG' columns name
            
            # Use post-processed table with custom formatting
            table_html = post_process_ranking_table(display_table, player_col=row_dimension)
            st.write(table_html, unsafe_allow_html=True)
            
            # # Add position summary
            # st.markdown("##### Position Summary")
            st.markdown('')
            st.markdown('')
            st.markdown(f"**{friendly_name} rankings summary**")

            position_summary = create_combined_position_summary(ranking_table, row_dimension)
            datawrapper_table(position_summary, css_classes='position-table')
                
        else:
            st.warning("No data available for the selected criteria.")