"""Streamlit page for score matrix table by player.

This page displays scores in a table format with players as columns and
TEGs/Rounds/9s as rows. It features:
- Segmented control to select aggregation level (TEG, Round, or 9-hole)
- Segmented control to select score type (Gross vs Par, Score, Stableford, Net vs Par)
- Dynamic table that updates based on selections
- Proper formatting for different score types

The page uses helper functions to:
- Load the complete dataset
- Aggregate scores at different levels
- Format values appropriately
- Display in a clean, readable table
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import load_all_data, load_datawrapper_css


# === CONFIGURATION ===
# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
st.title('Score Matrix')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === USER INTERFACE ===
# Aggregation level selector
aggregation_level = st.segmented_control(
    'Aggregation level',
    ['TEG', 'Round', '9'],
    default='TEG'
)

# Score type selector
score_type = st.segmented_control(
    'Score type',
    ['Gross vs Par', 'Score', 'Stableford', 'Net vs Par'],
    default='Gross vs Par'
)


# === DATA LOADING ===
# Load all TEG data for score matrix
all_data = load_all_data(exclude_incomplete_tegs=False)


# === DATA PROCESSING ===
# Map score type to field name
score_field_mapping = {
    'Gross vs Par': 'GrossVP',
    'Score': 'Sc',
    'Stableford': 'Stableford',
    'Net vs Par': 'NetVP'
}
selected_field = score_field_mapping[score_type]

# Determine grouping columns based on aggregation level
if aggregation_level == 'TEG':
    group_cols = ['TEGNum', 'Pl']
    id_col = 'TEG'
elif aggregation_level == 'Round':
    group_cols = ['TEGNum', 'Round', 'Pl']
    id_col = 'TEG|Round'
else:  # '9'
    group_cols = ['TEGNum', 'Round', 'FrontBack', 'Pl']
    id_col = 'TEG|Round|9'

# Aggregate data
agg_data = all_data.groupby(group_cols)[selected_field].sum().reset_index()

# Create identifier column for rows and preserve sort columns
if aggregation_level == 'TEG':
    agg_data[id_col] = 'TEG ' + agg_data['TEGNum'].astype(str)
    sort_cols = ['TEGNum']
    pivot_index = ['TEGNum', id_col]
elif aggregation_level == 'Round':
    agg_data[id_col] = 'TEG ' + agg_data['TEGNum'].astype(str) + ' | R' + agg_data['Round'].astype(str)
    sort_cols = ['TEGNum', 'Round']
    pivot_index = ['TEGNum', 'Round', id_col]
else:  # '9'
    agg_data[id_col] = (
        'TEG ' + agg_data['TEGNum'].astype(str) +
        ' | R' + agg_data['Round'].astype(str) +
        ' | ' + agg_data['FrontBack']
    )
    # For sorting: Front comes before Back, so we'll use a helper column
    agg_data['fb_sort'] = agg_data['FrontBack'].map({'Front': 0, 'Back': 1})
    sort_cols = ['TEGNum', 'Round', 'fb_sort']
    pivot_index = ['TEGNum', 'Round', 'fb_sort', id_col]

# Sort the data
agg_data = agg_data.sort_values(sort_cols)

# Pivot to create player columns, keeping sort columns for proper ordering
pivot_data = agg_data.pivot(index=pivot_index, columns='Pl', values=selected_field)

# Get player columns in sorted order
all_players = sorted(all_data['Pl'].unique())
# Reorder columns to ensure all players are present (even if they have no data)
pivot_data = pivot_data.reindex(columns=all_players)

# Reset index to make columns available
pivot_data = pivot_data.reset_index()

# Keep only the display column and player columns
# Drop the numeric sort columns
pivot_data = pivot_data[[id_col] + all_players]

# Rename the columns to remove any MultiIndex structure
pivot_data.columns.name = None

# Calculate average column (before formatting)
# Average: Mean across all non-null players
pivot_data['Average'] = pivot_data[all_players].mean(axis=1, skipna=True)


# === FORMATTING ===
# Format values based on score type
def format_player_value(val, score_type):
    """Format a player value to 0 decimal places."""
    if pd.isna(val):
        return '-'

    if score_type in ['Gross vs Par', 'Net vs Par']:
        # Format with +/- prefix and 0 decimal places
        return f"{val:+.0f}"
    else:
        # Format as integer (Score or Stableford)
        return f"{int(val)}"

def format_average_value(val, score_type):
    """Format an average value to 1 decimal place."""
    if pd.isna(val):
        return '-'

    if score_type in ['Gross vs Par', 'Net vs Par']:
        # Format with +/- prefix and 1 decimal place
        return f"{val:+.1f}"
    else:
        # Format as float with 1 decimal place (Score or Stableford)
        return f"{val:.1f}"

# Apply formatting to all player columns (0 decimal places)
for col in all_players:
    if col in pivot_data.columns:
        pivot_data[col] = pivot_data[col].apply(lambda x: format_player_value(x, score_type))

# Format average column (1 decimal place)
pivot_data['Average'] = pivot_data['Average'].apply(lambda x: format_average_value(x, score_type))


# === DISPLAY ===
st.write(
    pivot_data.to_html(
        index=False,
        justify='left',
        classes='datawrapper-table full-width'
    ),
    unsafe_allow_html=True
)
