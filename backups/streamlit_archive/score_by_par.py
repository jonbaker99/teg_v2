from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, load_datawrapper_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
load_datawrapper_css()
st.title("Scoring")

st.subheader('Average score by Par')

all_data = load_all_data(exclude_incomplete_tegs=False)
avg_grossvp = all_data.groupby(['Player', 'PAR'])['GrossVP'].mean().unstack(fill_value=0)
avg_grossvp['Total'] = all_data.groupby('Player')['GrossVP'].mean()
avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
avg_grossvp = avg_grossvp.round(2)


def format_value(value):
    if value > 0:
        return f"+{value:.2f}"
    elif value < 0:
        return f"{value:.2f}"
    else:
        return "="

for column in avg_grossvp.columns:
    avg_grossvp[column] = avg_grossvp[column].apply(format_value)

avg_grossvp.reset_index(inplace=True)
avg_grossvp.columns.name = None
avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]

st.write(avg_grossvp.to_html(classes='dataframe, datawrapper-table', index=False, justify='left'), unsafe_allow_html=True)