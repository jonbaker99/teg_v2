import streamlit as st
import pandas as pd
from utils import load_all_data, datawrapper_table_css

all_data = load_all_data(exclude_incomplete_tegs = False)
datawrapper_table_css()

st.title('Count of score by player')

all_data = load_all_data(exclude_incomplete_tegs = True)

def count_by_pl(df = all_data, field = 'GrossVP'):

    summary = all_data.groupby([field, 'Pl']).size().unstack(fill_value=0)
    
    # Sort the index (GrossVP) in descending order
    summary = summary.sort_index(ascending=True)
    
    # Optional: Sort columns (players) alphabetically
    summary = summary.sort_index(axis=1)
    
    return summary
    

count_gvp = count_by_pl(all_data, 'GrossVP')
count_sc = count_by_pl(all_data, 'Sc')

st.markdown('### Count of Gross vs Par by player')
st.write(count_gvp)
#st.write(count_gvp.to_html(classes='datawrapper-table'), unsafe_allow_html=True)
'---'

st.markdown('### Count of gross score by player')
st.write(count_sc)
#st.write(count_sc.to_html(classes='datawrapper-table'), unsafe_allow_html=True)