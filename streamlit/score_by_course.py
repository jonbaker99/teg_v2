from utils import load_all_data, get_best, get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css, get_round_data, load_course_info
import streamlit as st
import numpy as np, pandas as pd

# Import area filtering functions
from helpers.course_analysis_processing import (
    prepare_area_filter_options,
    filter_data_by_area
)

st.title('Rounds by Course')
load_datawrapper_css()

expander = st.expander("Select options", expanded=True)

rd_data = get_ranked_round_data()
rd_data['Pl_count'] = rd_data.groupby('Pl')['Pl'].transform('count')
rd_data['All_count'] = len(rd_data)

# Load course information for area filtering
course_info = load_course_info()

# Prepare area filter options
area_options, all_area_label = prepare_area_filter_options(course_info)

with expander:
    # Area filtering selection
    selected_area = st.selectbox('Filter by area:', area_options)

# Apply area filter to data
filtered_rd_data = filter_data_by_area(rd_data, course_info, selected_area, all_area_label)

# Update course options based on filtered data
unique_courses = ['All courses'] + sorted(filtered_rd_data['Course'].unique().tolist())

with expander:
    selected_course = st.selectbox('Select a course:', unique_courses)

if selected_course == 'All courses':
    filter_data = filtered_rd_data
    all_courses = True
else:
    filter_data = filtered_rd_data[filtered_rd_data['Course'] == selected_course]
    all_courses = False


# Get unique players from the filtered data and sort them alphabetically
unique_players = sorted(filtered_rd_data['Player'].unique().tolist())
player_options = ['All players'] + unique_players


with expander:
    # Create a selectbox for players
    selected_player = st.selectbox('Select a player:', player_options)
    #selected_player = st.radio('Select a player:', player_options, horizontal= True)

if selected_player == 'All players':
    filter_data = filter_data
else:
    filter_data = filter_data[filter_data['Player'] == selected_player]


course_data = filter_data

# course_data = rd_data[rd_data['Course'] == selected_course]



name_mapping = {
    'Score': 'Sc',
    'Gross vs Par': 'GrossVP',
    'Stableford': 'Stableford',
    'Net vs Par': 'NetVP'
}
inverted_name_mapping = {v: k for k, v in name_mapping.items()}

# Use the friendly names for the radio buttons
friendly_names = list(name_mapping.keys())

with expander:
    selected_friendly_name = st.radio("Choose a measure:", friendly_names, horizontal=True)

course_data = course_data.rename(columns=inverted_name_mapping)

# Convert to function name
selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
pl_rnk = f'Rank_within_player_'+selected_measure

sort_asc = (selected_friendly_name != 'Stableford')
course_friendly = course_data.sort_values(by = selected_friendly_name, ascending = sort_asc)
field_list = ['Player','Course',selected_friendly_name,'TEG-Round','Year',pl_rnk,'Pl_count']
course_output = course_friendly[field_list].rename(columns={pl_rnk: 'PB Rank'})
course_output['PB Rank'] = course_output['PB Rank'].astype(int).astype(str) +'/'+course_output['Pl_count'].astype(int).astype(str)
course_output = course_output.drop('Pl_count', axis=1)
numeric_columns = course_output.select_dtypes(include=['float64', 'int64']).columns
course_output[numeric_columns] = course_output[numeric_columns].astype(int)

st.markdown(f'### All rounds for {selected_player} at {selected_course}')
st.write(course_output.to_html(escape=False, index=False, justify='left', classes='datawrapper-table left-second'), unsafe_allow_html=True)

# '---'
# course_output_all = course_friendly[['Pl']+friendly_names + ['TEG-Round','Year']].sort_values(by = selected_friendly_name, ascending = sort_asc)
# numeric_columns_all = course_output_all.select_dtypes(include=['float64', 'int64']).columns
# course_output_all[numeric_columns_all] = course_output_all[numeric_columns_all].astype(int)

# st.markdown(f'### All TEG rounds at {selected_course} (sorted by {selected_friendly_name})')
# st.write(course_output_all.to_html(escape=False, index=False, justify='left', classes='datawrapper-table'), unsafe_allow_html=True)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
add_custom_navigation_links(__file__, layout="horizontal", separator=" | ")
