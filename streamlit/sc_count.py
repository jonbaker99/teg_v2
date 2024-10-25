import streamlit as st
import pandas as pd
from utils import load_all_data, datawrapper_table_css, datawrapper_table, format_vs_par

all_data = load_all_data(exclude_incomplete_tegs = False)
datawrapper_table_css()

st.title('Count of score by player')


tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(),reverse=True)
selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

#selected_tegnum = 'All TEGs'

# Filter data based on TEGNum selection
if selected_tegnum != 'All TEGs':
    selected_tegnum = int(selected_tegnum)
    filtered_data = all_data[all_data['TEGNum'] == selected_tegnum]
else:
    filtered_data = all_data

def count_by_pl(df = all_data, field = 'GrossVP'):

    summary = df.groupby([field, 'Pl']).size().unstack(fill_value=0)
    
    # Sort the index (GrossVP) in descending order
    summary = summary.sort_index(ascending=True)
    
    # Optional: Sort columns (players) alphabetically
    summary = summary.sort_index(axis=1)
    
    return summary
    

count_gvp = count_by_pl(filtered_data, 'GrossVP')
count_sc = count_by_pl(filtered_data, 'Sc')


tab1, tab2  = st.tabs(["Scores", "Scores vs Par"])

with tab1:
    st.markdown('### Count of Gross vs Par by player')
    # st.dataframe(count_gvp, height = len(count_gvp) * 35 + 38)
    count_gvp = count_gvp.reset_index()
    count_gvp['GrossVP'] = count_gvp['GrossVP'].apply(format_vs_par)
    count_gvp = count_gvp.rename(columns={'GrossVP': 'vs Par'})
    count_gvp.columns.name = None
    datawrapper_table(count_gvp)

with tab2:
    st.markdown('### Count of gross score by player')
    # st.dataframe(count_sc, height = len(count_sc) * 35 + 38)
    count_sc = count_sc.reset_index()
    count_sc.columns.name = None
    count_sc['Sc'] = count_sc['Sc'].astype(int)
    count_gvp = count_gvp.rename(columns={'Sc': 'Score'})
    datawrapper_table(count_sc)
