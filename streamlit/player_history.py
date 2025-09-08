# === IMPORTS ===
import streamlit as st
import pandas as pd
import logging
import re

# Import data loading functions from main utils
from utils import get_complete_teg_data, load_datawrapper_css, datawrapper_table

# === CONFIGURATION ===
st.title("TEG Rankings by Scoring Type")

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
st.markdown("Select a scoring type to see how each player ranked in each completed TEG.")
st.markdown("**Note**: Only completed TEGs are included. Empty cells indicate the player did not participate in that TEG.")

# Scoring type selection
scoring_options = {
    # 'Gross Score': 'Sc',
    'Stableford Points': 'Stableford',
    'Gross vs Par': 'GrossVP', 
    'Net vs Par': 'NetVP'
}

selected_friendly = st.selectbox(
    "Choose scoring type:",
    options=list(scoring_options.keys()),
    index=0  # Default to 'Stableford'
)

selected_scoring_type = scoring_options[selected_friendly]

# Bonus feature: Row/Column selection
st.markdown("---")
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

with st.spinner("Calculating rankings..."):
    # Load completed TEG data using existing function
    teg_data = get_complete_teg_data()
    
    # Create the ranking table using our new function
    ranking_table = create_teg_ranking_table(
        teg_data=teg_data,
        scoring_type=selected_scoring_type,
        row_dimension=row_dimension,
        col_dimension=col_dimension
    )

# Display title and explanation
st.markdown(f"#### {selected_friendly} Rankings by TEG")

# Add explanation based on scoring type
# if selected_scoring_type == 'Stableford':
#     st.caption("Higher stableford points = better performance (1st place = highest score)")
# else:
#     st.caption("Lower scores = better performance (1st place = lowest score)")

st.caption("Numbers show rank within that TEG. Ties are marked with '='. Empty cells = did not participate.")

# Format the table for display
if not ranking_table.empty:
    # Replace NaN with empty string for cleaner display
    # After you build ranking_table
    display_table = (
        ranking_table
            # .fillna('-') leave this as we'll replace na later
            .reset_index(drop=True)   # 1) drop the numeric index column
    )
    display_table.index.name = None   # just in case
    display_table.columns.name = None # 2) remove the 'TEG' columns name
    
    # Use post-processed table with custom formatting
    table_html = post_process_ranking_table(display_table, player_col=row_dimension)
    st.write(table_html, unsafe_allow_html=True)
    

else:
    st.warning("No data available for the selected criteria.")