from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, datawrapper_table_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
datawrapper_table_css()
st.title("Career Eagles, Birdies, Pars and Triple Bogey+")

# Calculate the stats
scoring_stats = score_type_stats()


chart_fields_all = [
    ['Eagles', 'Holes_per_Eagle'],
    ['Birdies', 'Holes_per_Birdie'],
    ['Pars_or_Better', 'Holes_per_Par_or_Better'],
    ['TBPs', 'Holes_per_TBP']
]

cnt_fields = len(chart_fields_all)

tab_labels = [chart_fields_all[i][0].replace("_", " ") for i in range(cnt_fields)]
tabs = st.tabs(tab_labels)

def format_dataframe_columns(df):
    # Create a copy of the dataframe to avoid modifying the original
    formatted_df = df.copy()
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}")
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]
    
    return formatted_df


for i, tab in enumerate(tabs):
    with tab:
        chart_fields = chart_fields_all[i]
        section_title = chart_fields[0].replace("_", " ")
        st.markdown(f"**Career {section_title}**")
        
        table_df = scoring_stats[['Player'] + chart_fields].sort_values(by=chart_fields, ascending=[False, True])
        table_df = format_dataframe_columns(table_df)
        st.write(table_df.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)

'---'

st.subheader('Most in a single round')
max_by_round = max_scoretype_per_round()
st.write(max_by_round.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)