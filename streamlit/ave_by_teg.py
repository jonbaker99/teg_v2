import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_all_data, load_datawrapper_css

# Streamlit app title
st.title('Player Performance Over Time')

load_datawrapper_css()
# Assuming all_data is your DataFrame
# If not, replace this with your actual data loading code
# all_data = pd.read_csv('your_data.csv')

all_data = load_all_data()

# Calculate mean GrossVP for each player and TEGNum, then multiply by 18
# Calculate mean GrossVP for each player and TEGNum, then multiply by 18
graph_data = all_data.groupby(['TEGNum', 'Pl'])['GrossVP'].mean().reset_index()
graph_data['GrossVP'] = graph_data['GrossVP'] * 18

# Format TEGNum as 'TEG {TEGNum}'
graph_data['TEGNum'] = 'TEG ' + graph_data['TEGNum'].astype(str)

# Create the line graph with markers
fig = px.line(graph_data, x='TEGNum', y='GrossVP', color='Pl',
              labels={'TEGNum': '', 'GrossVP': 'Average Gross VP * 18', 'Pl': 'Player'},
              line_shape='linear', render_mode='svg')

# Add markers to the lines
fig.update_traces(mode='lines+markers', marker=dict(size=8))

# Customize the layout
fig.update_layout(
    # xaxis_title='TEG Number',
    xaxis_title='',
    yaxis_title='Average Gross vs Par',
    legend_title='Player',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    hovermode='x unified',
    margin=dict(t=50, l=0),  # Increase top margin to accommodate the legend
    font=dict(family="monospace"),  # Set all text to monospace
    xaxis=dict(tickfont=dict(color='black'), tickangle=270),  # Set x-axis tick label color to black and rotate 90 degrees
    yaxis=dict(tickfont=dict(color='black'))   # Set y-axis tick label color to black
)

# Remove the title
#fig.update_layout(title=None)

# Display the graph
st.markdown('### Ave Gross vs Par by TEG')
st.plotly_chart(fig,  use_container_width=True, config=dict({'displayModeBar': False}))

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

# Format numbers to 1 decimal place
for col in merged_df.columns:
    if col != 'TEGNum':
        merged_df[col] = merged_df[col].apply(lambda x: f"{x:.1f}" if pd.notnull(x) and isinstance(x, (int, float)) else "-")

# Rename 'TEGNum' to 'TEG'
merged_df = merged_df.rename(columns={'TEGNum': 'TEG'})

# Display the table using Streamlit
#st.markdown('### Ave Gross vs Par by TEG')
st.write(merged_df.to_html(index=False, justify='left', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
