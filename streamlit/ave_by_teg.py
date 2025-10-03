"""Streamlit page for analyzing average scores by TEG.

This page visualizes player performance over time by showing the average
Gross vs. Par score for each player in every TEG. It includes:
- A line chart comparing the performance trends of all players across all
  tournaments.
- A summary table with the same data for detailed inspection.

The page uses helper functions to:
- Load the complete dataset.
- Calculate and format the average scores.
- Display the data in a line chart and a table.
"""
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_all_data, load_datawrapper_css

# Streamlit app title
st.title('Player Performance Over Time')

load_datawrapper_css()
# Assuming all_data is your DataFrame
# If not, replace this with your actual data loading code
# all_data = pd.read_csv('your_data.csv')

all_data = load_all_data()

# Altair theme function
def altair_theme():
    return {
        "config": {
            "background": "White",
            "view": {"strokeWidth": 0, "fill": "#F8F8F8"},
            "axis": {
                "domain": False, "grid": False, "ticks": False,
                "labelColor": "#333", "titleColor": "#333",
                "labelFontSize": 12, "titleFontSize": 12,
                "labelFont": "roboto mono, monospace",
                "titleFont": "roboto mono, monospace"
            },
            "legend": {
                "title": None,
                "labelFontSize": 12,
                "labelFont": "roboto mono, monospace"
            },
            "title": {
                "font": "roboto mono, monospace",
                "fontSize": 16,
                "color": "#222",
                "anchor":"start",
                "offset": 25
                }
        }
    }

# Calculate mean GrossVP for each player and TEGNum, then multiply by 18
graph_data = all_data.groupby(['TEGNum', 'Pl'])['GrossVP'].mean().reset_index()
graph_data['GrossVP'] = graph_data['GrossVP'] * 18

# Create sort order and display label
graph_data['sort_order'] = graph_data['TEGNum']
graph_data['TEG'] = 'TEG ' + graph_data['TEGNum'].astype(str)

# Rename columns for Altair
graph_data = graph_data.rename(columns={'GrossVP': 'Gross vs Par', 'Pl': 'Player'})

# Create selection for legend-based highlighting
selection = alt.selection_point(fields=["Player"], bind="legend", toggle=True)

# Base encodings
base = alt.Chart(graph_data).encode(
    x=alt.X(
        "TEG:N",
        title=None,
        sort=alt.EncodingSortField(field="sort_order", order="ascending"),
        axis=alt.Axis(labelAngle=270)
    ),
    y=alt.Y(
        "Gross vs Par:Q",
        title="Gross vs Par",
        scale=alt.Scale(nice=True, zero=True),
        axis=alt.Axis(grid=True, gridColor="#E9E9E9", labels=True, titleFontSize=12)
        ),
    color=alt.Color(
        "Player:N",
        legend=alt.Legend(orient="top", direction="horizontal", titleLimit=0)
    ),
    opacity=alt.condition(selection, alt.value(1), alt.value(0.2))
)

# Line layer
line_layer = base.mark_line(size=2.5, interpolate="linear").add_params(selection)

# Point layer
point_layer = base.mark_point(filled=True, size=50, stroke="white", strokeWidth=1)

# Build chart
chart = alt.layer(line_layer, point_layer).properties(
    width=600, 
    height=600, 
    # title="Average Gross Score by TEG",
    padding={"left": 10, "right": 10, "top": 10, "bottom": 10}
).configure(**altair_theme()["config"])

# Display the graph
st.markdown('#### Gross vs Par by player by TEG')
st.caption("Click on player in legend to highlight")
st.altair_chart(chart, use_container_width=False)

#===========================================
#===========================================
#===========================================



# Create a copy of the dataframe to avoid modifying the original one
df_copy = all_data.copy()

# Get unique player values
players = df_copy['Pl'].unique()

# Initialize an empty list to store individual player dataframes
player_dfs = []

# Loop through each player
for player in players:
    # Filter the dataframe for the specific player
    player_df = df_copy[df_copy['Pl'] == player]
    
    # Calculate the average GrossVP by TEG
    player_avg = player_df.groupby('TEGNum')['GrossVP'].mean().reset_index()
    
    # Rename 'GrossVP' column to the player's name (initials)
    player_avg = player_avg.rename(columns={'GrossVP': player})
    
    # Append this dataframe to the list
    player_dfs.append(player_avg)

# Merge all the player dataframes on 'TEGNum'
merged_df = player_dfs[0]
for player_df in player_dfs[1:]:
    merged_df = pd.merge(merged_df, player_df, on='TEGNum', how='outer')

# Multiply all values (except TEGNum) by 18
merged_df.iloc[:, 1:] = merged_df.iloc[:, 1:] * 18

# Format TEGNum as 'TEG {TEGNum}'
merged_df['TEGNum'] = 'TEG ' + merged_df['TEGNum'].astype(str)

# Reset the index to make 'TEG {TEGNum}' a column
merged_df = merged_df.reset_index(drop=True)

# Format numbers to 1 decimal place with + prefix
for col in merged_df.columns:
    if col != 'TEGNum':
        merged_df[col] = merged_df[col].apply(lambda x: f"{x:+.1f}" if pd.notnull(x) and isinstance(x, (int, float)) else "-")

# Rename 'TEGNum' to 'TEG'
merged_df = merged_df.rename(columns={'TEGNum': 'TEG'})

# Display the table using Streamlit in an expander
with st.expander("Data table", expanded=False):
    st.markdown('<div style="display: flex; justify-content: center;">', unsafe_allow_html=True)
    st.write(merged_df.to_html(index=False, justify='center', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
