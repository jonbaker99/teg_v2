import streamlit as st
import pandas as pd
from utils import load_all_data, load_datawrapper_css, format_vs_par

all_data = load_all_data(exclude_incomplete_tegs = False)
load_datawrapper_css()


st.title('Scorecard for selected round')

# Create dropdowns for Pl, TEGNum, and Round
pl_options = sorted(all_data['Pl'].unique())
default_pl = pl_options[0] if pl_options else None

tegnum_options = sorted(all_data['TEGNum'].unique())
default_tegnum = max(tegnum_options) if tegnum_options else None

# Function to get the highest Round for a given TEGNum
def get_max_round(tegnum):
    return all_data[all_data['TEGNum'] == tegnum]['Round'].max()

# Sidebar for selections

st.markdown('**Select round to view scorecard for**')
selected_pl = st.selectbox('Select Player', pl_options, index=pl_options.index(default_pl))
    
selected_tegnum = st.selectbox('Select TEGNum', tegnum_options, index=tegnum_options.index(default_tegnum))
    
max_round = get_max_round(selected_tegnum)
round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
selected_round = st.selectbox('Select Round', round_options, index=round_options.index(max_round) if max_round in round_options else 0)

st.caption(f"Scorecard | TEG {selected_tegnum} round {selected_round} | Player: {selected_pl} ")

# Filter data based on selections
rd_data = all_data[
    (all_data['Pl'] == selected_pl) &
    (all_data['TEGNum'] == selected_tegnum) &
    (all_data['Round'] == selected_round)
]

# Display the filtered data
output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
output_data = rd_data[output_cols]





# add totals for selected columns

# List of columns you want to sum
columns_to_sum = ['PAR','HCStrokes','Sc', 'GrossVP', 'NetVP', 'Stableford']

# Filter to only existing columns
existing_columns = [col for col in columns_to_sum if col in output_data.columns]

# Create a Series with sums for those columns
totals = pd.Series({col: output_data[col].sum() for col in existing_columns})

# Add to dataframe
output_data.loc['Total'] = totals


def to_int_or_dash(x):
    if pd.isna(x):
        return ""
    return int(x)

# Convert only numeric columns while preserving other columns
numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
#output_data[numeric_columns] = output_data[numeric_columns].fillna(0).astype(int)
for col in numeric_columns:
    output_data[col] = output_data[col].map(to_int_or_dash)

# Format gross and net

columns_to_format = ['GrossVP', 'NetVP']
for col in columns_to_format:
    if col in output_data.columns:
        output_data[col] = output_data[col].apply(format_vs_par)


st.write(output_data.to_html(index=False, justify='left', classes = 'datawrapper-table bold-last-row'), unsafe_allow_html = True)
