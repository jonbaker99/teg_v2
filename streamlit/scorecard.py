import streamlit as st
import pandas as pd
from utils import load_all_data, datawrapper_table_css

all_data = load_all_data(exclude_incomplete_tegs = False)
datawrapper_table_css()


st.title('Golf Data Viewer')

# Create dropdowns for Pl, TEGNum, and Round
pl_options = sorted(all_data['Pl'].unique())
default_pl = pl_options[0] if pl_options else None

tegnum_options = sorted(all_data['TEGNum'].unique())
default_tegnum = max(tegnum_options) if tegnum_options else None

# Function to get the highest Round for a given TEGNum
def get_max_round(tegnum):
    return all_data[all_data['TEGNum'] == tegnum]['Round'].max()

# Sidebar for selections

st.header('Select Options')
selected_pl = st.selectbox('Select Player', pl_options, index=pl_options.index(default_pl))
    
selected_tegnum = st.selectbox('Select TEGNum', tegnum_options, index=tegnum_options.index(default_tegnum))
    
max_round = get_max_round(selected_tegnum)
round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
selected_round = st.selectbox('Select Round', round_options, index=round_options.index(max_round) if max_round in round_options else 0)

# Filter data based on selections
rd_data = all_data[
    (all_data['Pl'] == selected_pl) &
    (all_data['TEGNum'] == selected_tegnum) &
    (all_data['Round'] == selected_round)
]

# Display the filtered data
output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
output_data = rd_data[output_cols]

# Convert only numeric columns while preserving other columns
numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
output_data[numeric_columns] = output_data[numeric_columns].astype(int)


st.write(output_data.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html = True)

# Additional statistics or visualizations can be added here
st.caption(f"Showing data for Player: {selected_pl}, TEGNum: {selected_tegnum}, Round: {selected_round}")