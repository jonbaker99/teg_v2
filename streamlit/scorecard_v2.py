import streamlit as st
import pandas as pd
import numpy as np
from utils import load_all_data, format_vs_par

# Inline CSS (more reliable than external file)
def load_scorecard_css():
    """Load scorecard CSS inline"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    
    .scorecard-container {
        background: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        max-width: 1400px;
        margin: 0 auto 30px auto;
        font-family: 'Roboto', Arial, sans-serif;
    }
    
    .scorecard-header {
        text-align: center;
        margin-bottom: 20px;
    }
    
    .scorecard-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 2px;
        font-size: 14px;
        margin-bottom: 20px;
    }
    
    .scorecard-table th,
    .scorecard-table td {
        padding: 6px;
        text-align: center;
        border: none;
        font-weight: bold;
        min-width: 32px;
        height: 32px;
        vertical-align: middle;
        position: relative;
        background-color: #f8f9fa;
    }
    
    .score-cell {
        position: relative;
        background-color: white;
    }
    
    .score-cell::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 28px;
        height: 28px;
        border-radius: 4px;
        z-index: 1;
    }
    
    .score-cell span {
        position: relative;
        z-index: 2;
    }
    
    /* Score colors */
    .score-cell[data-vs-par="-2"]::before { background-color: #FFD700; }
    .score-cell[data-vs-par="-1"]::before { background-color: #90EE90; }
    .score-cell[data-vs-par="0"]::before { background-color: #E6F3FF; }
    .score-cell[data-vs-par="1"]::before { background-color: #FFE4B5; }
    .score-cell[data-vs-par="2"]::before { background-color: #FFA07A; }
    .score-cell[data-vs-par="3"]::before,
    .score-cell[data-vs-par="4"]::before,
    .score-cell[data-vs-par="5"]::before,
    .score-cell[data-vs-par="6"]::before,
    .score-cell[data-vs-par="7"]::before,
    .score-cell[data-vs-par="8"]::before,
    .score-cell[data-vs-par="9"]::before,
    .score-cell[data-vs-par="10"]::before { background-color: #8B0000; }
    
    /* Stableford colors */
    .score-cell[data-stableford="0"]::before { background-color: #ffffff; border: 1px solid #ddd; }
    .score-cell[data-stableford="1"]::before { background-color: #e3f2fd; }
    .score-cell[data-stableford="2"]::before { background-color: #bbdefb; }
    .score-cell[data-stableford="3"]::before { background-color: #90caf9; }
    .score-cell[data-stableford="4"]::before { background-color: #64b5f6; }
    .score-cell[data-stableford="5"]::before,
    .score-cell[data-stableford="6"]::before,
    .score-cell[data-stableford="7"]::before,
    .score-cell[data-stableford="8"]::before { background-color: #1976d2; }
    
    /* White text for dark backgrounds */
    .score-cell[data-vs-par="3"] span,
    .score-cell[data-vs-par="4"] span,
    .score-cell[data-vs-par="5"] span,
    .score-cell[data-vs-par="6"] span,
    .score-cell[data-vs-par="7"] span,
    .score-cell[data-vs-par="8"] span,
    .score-cell[data-vs-par="9"] span,
    .score-cell[data-vs-par="10"] span,
    .score-cell[data-stableford="5"] span,
    .score-cell[data-stableford="6"] span,
    .score-cell[data-stableford="7"] span,
    .score-cell[data-stableford="8"] span {
        color: white;
    }
    
    /* Layout styling */
    .layout-single-round .label-column {
        text-align: left;
        min-width: 80px;
        padding-left: 8px;
    }
    
    .layout-single-round .hole-header {
        border-bottom: 2px solid #333;
    }
    
    .layout-single-round .front-back-divider {
        border-right: 3px solid #333;
    }
    
    .totals {
        font-weight: bold;
        background-color: #f8f9fa;
    }
    
    @media (max-width: 768px) {
        .scorecard-table { font-size: 12px; }
        .scorecard-table th, .scorecard-table td { 
            padding: 4px; 
            min-width: 28px; 
            height: 28px; 
        }
        .layout-single-round .label-column {
            min-width: 60px;
            font-size: 11px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def generate_scorecard_html(df, layout="single-round", title="Scorecard"):
    """
    Convert a pandas DataFrame to a golf scorecard HTML.
    """
    
    # Ensure we have 18 holes
    if len(df) != 18:
        st.error(f"Expected 18 holes, got {len(df)} holes")
        return ""
    
    # Calculate front 9, back 9, and total
    front_9 = df[df['Hole'] <= 9]
    back_9 = df[df['Hole'] > 9]
    
    front_totals = {
        'PAR': int(front_9['PAR'].sum()),
        'Sc': int(front_9['Sc'].sum()),
        'Stableford': int(front_9['Stableford'].sum())
    }
    
    back_totals = {
        'PAR': int(back_9['PAR'].sum()),
        'Sc': int(back_9['Sc'].sum()), 
        'Stableford': int(back_9['Stableford'].sum())
    }
    
    total_totals = {
        'PAR': int(df['PAR'].sum()),
        'Sc': int(df['Sc'].sum()),
        'Stableford': int(df['Stableford'].sum())
    }
    
    # Generate hole header row
    hole_header = '<th class="label-column hole-header">Hole</th>'
    for hole in range(1, 19):
        if hole == 10:
            hole_header += f'<th class="hole-header totals front-back-divider">OUT</th>'
        hole_header += f'<th class="hole-header">{hole}</th>'
    hole_header += '<th class="hole-header totals">IN</th><th class="hole-header totals">TOTAL</th>'
    
    # Generate PAR row
    par_row = '<th class="label-column">PAR</th>'
    for hole in range(1, 19):
        if hole == 10:
            par_row += f'<th class="totals front-back-divider">{front_totals["PAR"]}</th>'
        par_value = int(df[df['Hole'] == hole]['PAR'].iloc[0])
        par_row += f'<th>{par_value}</th>'
    par_row += f'<th class="totals">{back_totals["PAR"]}</th><th class="totals">{total_totals["PAR"]}</th>'
    
    # Generate score row with data attributes
    score_row = '<td class="label-column">Score</td>'
    for hole in range(1, 19):
        if hole == 10:
            score_row += f'<td class="totals front-back-divider">{front_totals["Sc"]}</td>'
        
        hole_data = df[df['Hole'] == hole].iloc[0]
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        
        score_row += f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>'
    
    score_row += f'<td class="totals">{back_totals["Sc"]}</td><td class="totals">{total_totals["Sc"]}</td>'
    
    # Generate Stableford row with data attributes  
    stableford_row = '<td class="label-column">Stableford</td>'
    for hole in range(1, 19):
        if hole == 10:
            stableford_row += f'<td class="totals front-back-divider">{front_totals["Stableford"]}</td>'
        
        hole_data = df[df['Hole'] == hole].iloc[0]
        stableford = int(hole_data['Stableford'])
        
        stableford_row += f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>'
    
    stableford_row += f'<td class="totals">{back_totals["Stableford"]}</td><td class="totals">{total_totals["Stableford"]}</td>'
    
    # Combine into full HTML
    html = f'''
    <div class="scorecard-container layout-{layout}">
        <div class="scorecard-header">
            <h2>{title}</h2>
        </div>
        
        <table class="scorecard-table">
            <thead>
                <tr>{hole_header}</tr>
                <tr>{par_row}</tr>
            </thead>
            <tbody>
                <tr>{score_row}</tr>
                <tr>{stableford_row}</tr>
            </tbody>
        </table>
    </div>
    '''
    
    return html

# Load CSS first
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

# Debug info
with st.expander("Debug Info"):
    st.write("Data shape:", output_data.shape)
    st.write("Columns:", output_data.columns.tolist())
    st.write("Sample data:")
    st.dataframe(output_data.head())

# Generate the enhanced scorecard
title = f"TEG {selected_tegnum} Round {selected_round} | {selected_pl}"

try:
    scorecard_html = generate_scorecard_html(output_data, layout="single-round", title=title)
    
    # Display the scorecard
    if scorecard_html:
        st.write(scorecard_html, unsafe_allow_html=True)
    else:
        st.error("Failed to generate scorecard HTML")
        
except Exception as e:
    st.error(f"Error generating scorecard: {str(e)}")
    st.write("Falling back to original table format:")
    
    # Fallback to original format
    old_output_data = output_data.copy()
    columns_to_sum = ['PAR','HCStrokes','Sc', 'GrossVP', 'NetVP', 'Stableford']
    existing_columns = [col for col in columns_to_sum if col in old_output_data.columns]
    totals = pd.Series({col: old_output_data[col].sum() for col in existing_columns})
    old_output_data.loc['Total'] = totals
    
    columns_to_format = ['GrossVP', 'NetVP']
    for col in columns_to_format:
        if col in old_output_data.columns:
            old_output_data[col] = old_output_data[col].apply(format_vs_par)
    
    st.write(old_output_data.to_html(index=False, justify='left', classes='dataframe'), unsafe_allow_html=True)