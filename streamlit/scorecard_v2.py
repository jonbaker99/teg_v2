import streamlit as st
import pandas as pd
import numpy as np
from utils import load_all_data
from scorecard_utils import load_scorecard_css, generate_scorecard_html, format_vs_par

# Load CSS
load_scorecard_css()

st.title('Scorecard v2 - Enhanced Visual Design')

# Load data
all_data = load_all_data(exclude_incomplete_tegs=False)

# Create dropdowns for Pl, TEGNum, and Round
pl_options = sorted(all_data['Pl'].unique())
default_pl = pl_options[0] if pl_options else None

tegnum_options = sorted(all_data['TEGNum'].unique())
default_tegnum = max(tegnum_options) if tegnum_options else None

# Function to get the highest Round for a given TEGNum
def get_max_round(tegnum):
    return all_data[all_data['TEGNum'] == tegnum]['Round'].max()

# Sidebar for selections
st.markdown('**Select round to view enhanced scorecard**')

col1, col2, col3 = st.columns(3)

with col1:
    selected_pl = st.selectbox('Select Player', pl_options, index=pl_options.index(default_pl))

with col2:    
    selected_tegnum = st.selectbox('Select TEGNum', tegnum_options, index=tegnum_options.index(default_tegnum))

with col3:
    max_round = get_max_round(selected_tegnum)
    round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
    selected_round = st.selectbox('Select Round', round_options, index=round_options.index(max_round) if max_round in round_options else 0)

# Filter data based on selections
rd_data = all_data[
    (all_data['Pl'] == selected_pl) &
    (all_data['TEGNum'] == selected_tegnum) &
    (all_data['Round'] == selected_round)
]

if len(rd_data) == 0:
    st.error("No data found for the selected criteria.")
    st.stop()

# Prepare output data
output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
output_data = rd_data[output_cols].copy()

# Convert to appropriate data types
def to_int_or_zero(x):
    if pd.isna(x):
        return 0
    return int(x)

numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
for col in numeric_columns:
    output_data[col] = output_data[col].map(to_int_or_zero)

# Ensure we have exactly 18 holes
if len(output_data) != 18:
    st.error(f"Expected 18 holes, found {len(output_data)} holes for this round.")
    st.stop()

# Generate the enhanced scorecard
title = f"TEG {selected_tegnum} Round {selected_round} | {selected_pl}"
scorecard_html = generate_scorecard_html(output_data, layout="single-round", title=title)

# Display the scorecard
st.write(scorecard_html, unsafe_allow_html=True)

# Show comparison with old version
st.markdown("---")
st.subheader("Comparison: Old vs New")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Old Version (Plain Table)**")
    
    # Show old version for comparison
    old_output_data = output_data.copy()
    
    # Add totals for old version
    columns_to_sum = ['PAR','HCStrokes','Sc', 'GrossVP', 'NetVP', 'Stableford']
    existing_columns = [col for col in columns_to_sum if col in old_output_data.columns]
    totals = pd.Series({col: old_output_data[col].sum() for col in existing_columns})
    old_output_data.loc['Total'] = totals
    
    # Format vs par columns for old version
    columns_to_format = ['GrossVP', 'NetVP']
    for col in columns_to_format:
        if col in old_output_data.columns:
            old_output_data[col] = old_output_data[col].apply(format_vs_par)
    
    st.write(old_output_data.to_html(index=False, justify='left', classes='dataframe'), unsafe_allow_html=True)

with col2:
    st.markdown("**New Version (Enhanced Visual)**")
    st.markdown("✅ Color-coded performance")
    st.markdown("✅ Professional golf scorecard layout") 
    st.markdown("✅ Front 9 / Back 9 totals")
    st.markdown("✅ Instant visual feedback")
    st.markdown("✅ Mobile responsive")
    st.markdown("✅ Consistent with golf conventions")

# Show some statistics
st.markdown("---")
st.subheader("Round Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_score = output_data['Sc'].sum()
    total_par = output_data['PAR'].sum()
    vs_par = total_score - total_par
    vs_par_formatted = format_vs_par(vs_par)
    st.metric("Total Score", total_score, vs_par_formatted)

with col2:
    total_stableford = output_data['Stableford'].sum()
    st.metric("Stableford Points", total_stableford)

with col3:
    birdies = len(output_data[output_data['GrossVP'] == -1])
    eagles = len(output_data[output_data['GrossVP'] <= -2])
    st.metric("Birdies/Eagles", f"{birdies}/{eagles}")

with col4:
    bogeys_plus = len(output_data[output_data['GrossVP'] > 0])
    st.metric("Bogeys or Worse", bogeys_plus)

# Technical info
st.markdown("---")
with st.expander("Technical Details"):
    st.markdown("**Enhanced Scorecard Features:**")
    st.markdown("- **Data-driven colors**: Colors determined by score vs par automatically")
    st.markdown("- **Flexible CSS framework**: One CSS file supports multiple scorecard layouts")
    st.markdown("- **Separation of concerns**: CSS in separate file, Python utilities modular")
    st.markdown("- **Extensible**: Easy to add new layouts (tournament view, player comparison)")
    st.markdown("- **Golf-standard colors**: Gold eagles, green birdies, dark red for disasters")
    st.markdown("- **Professional layout**: Front/back nine divisions, proper totals")
    
    st.markdown("**Color Scheme:**")
    st.markdown("- 🟨 **Eagle (-2)**: Gold")
    st.markdown("- 🟢 **Birdie (-1)**: Light green") 
    st.markdown("- 🔵 **Par (0)**: Light blue")
    st.markdown("- 🟤 **Bogey (+1)**: Tan")
    st.markdown("- 🟠 **Double Bogey (+2)**: Orange")
    st.markdown("- 🔴 **Triple Bogey+ (+3)**: Dark red")
