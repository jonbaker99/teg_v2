from utils import load_all_data, get_best, get_ranked_teg_data, get_ranked_round_data, datawrapper_table_css
import streamlit as st
import numpy as np, pandas as pd

st.title('Personal Best TEGs and Rounds')
datawrapper_table_css()

teg_data_ranked = get_ranked_teg_data()
rd_data_ranked = get_ranked_round_data()
rd_data_ranked['Round'] = rd_data_ranked['TEG'] +'|R' + rd_data_ranked['Round'].astype(str)
# measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']

# selected_measure = st.radio("Select measure:", measures,horizontal=True)



name_mapping = {
    'Gross vs Par': 'GrossVP',
    'Score': 'Sc',
    'Net vs Par': 'NetVP',
    'Stableford': 'Stableford'
}
inverted_name_mapping = {v: k for k, v in name_mapping.items()}

# Use the friendly names for the radio buttons
friendly_names = list(name_mapping.keys())
selected_friendly_name = st.radio("Choose a measure:", friendly_names, horizontal=True)

# Convert to function name
selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)

DEFAULT_TOP_N = 1

# n_keep = st.number_input(
#     "Number of TEGs / Rounds to show",
#     min_value=1,
#     max_value=100,
#     value=DEFAULT_TOP_N,
#     step=1
# )

n_keep = DEFAULT_TOP_N

player_level = True
rank_measure = 'Rank_within_' + ('player' if player_level else 'all') + f'_{selected_measure}'
rank_all_time = 'Rank_within_all' + f'_{selected_measure}'
# create best teg table

best_t = (get_best(teg_data_ranked,selected_measure,player_level=player_level, top_n = n_keep)
          .sort_values(by=rank_all_time, ascending=True)
          .rename(columns={rank_all_time: '#'})
          .rename(columns=inverted_name_mapping))
best_t = best_t[['#','Player',selected_friendly_name,'TEG','Year']]

numeric_columns = best_t.select_dtypes(include=['float64', 'int64']).columns
best_t[numeric_columns] = best_t[numeric_columns].astype(int)

# create best round table

best_r = (get_best(rd_data_ranked,selected_measure,player_level=player_level, top_n = n_keep)
          .sort_values(by=rank_all_time, ascending=True)
          .rename(columns={rank_all_time: '#'})
          .rename(columns=inverted_name_mapping))
best_r = best_r[['#','Player',selected_friendly_name,'Round','Course','Year']]

numeric_columns = best_r.select_dtypes(include=['float64', 'int64']).columns
best_r[numeric_columns] = best_r[numeric_columns].astype(int)


tab1, tab2 = st.tabs(["Best TEGs","Best Rounds"])

with tab1:
    st.markdown(f'### Personal Best TEGs: {selected_friendly_name}')
    st.write(best_t.to_html(escape=False, index=False, justify='left', classes='datawrapper-table'), unsafe_allow_html=True)

with tab2:
    st.markdown(f'### Personal Best Rounds: {selected_friendly_name}')
    st.write(best_r.to_html(escape=False, index=False, justify='left', classes='datawrapper-table'), unsafe_allow_html=True)