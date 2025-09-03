import streamlit as st
import pandas as pd
from utils import load_all_data, load_datawrapper_css, format_vs_par

all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
all_data['TRH'] = all_data[['TEGNum', 'Round', 'Hole']].astype(str).agg('|'.join, axis=1)
bestball_cols = ['TEG','Round','Course','Year']
value_cols = ['GrossVP','Sc']

st.title("Best bestball and worst worstball")
load_datawrapper_css()

tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(),reverse=True)
selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

# Filter data based on TEGNum selection
if selected_tegnum != 'All TEGs':
    selected_tegnum = int(selected_tegnum)
    filtered_data = all_data[all_data['TEGNum'] == selected_tegnum]
else:
    filtered_data = all_data



@st.cache_data
def bestball(filtered_data):
    bestball = filtered_data.groupby('TRH').apply(lambda x: x.nsmallest(1, 'Sc')).reset_index(drop=True)
    bestball2 = bestball.groupby(bestball_cols)[value_cols].sum().reset_index()
    bestball2['Sc'] = bestball2['Sc'].astype(int)
    return(bestball2)

@st.cache_data
def worstball(filtered_data):
    worstball = filtered_data.groupby('TRH').apply(lambda x: x.nlargest(1, 'Sc')).reset_index(drop=True)
    worstball2 = worstball.groupby(bestball_cols)[value_cols].sum().reset_index()
    worstball2['Sc'] = worstball2['Sc'].astype(int)
    return(worstball2)

best_or_worst = st.radio("Rank by best or worst:", ('Best', 'Worst'), horizontal=True)

sort_asc = True if best_or_worst == 'Best' else False

bestball_output = bestball(filtered_data)[bestball_cols + value_cols].sort_values(by='GrossVP', ascending = sort_asc)
bestball_output['GrossVP'] = bestball_output['GrossVP'].apply(format_vs_par)

worstball_output = worstball(filtered_data)[bestball_cols + value_cols].sort_values(by='GrossVP', ascending = sort_asc)
worstball_output['GrossVP'] = worstball_output['GrossVP'].apply(format_vs_par)


tab1, tab2 = st.tabs(["Bestball", "Worstball"])

with tab1:
    st.markdown(f'**{best_or_worst} bestball**')
    st.write(bestball_output.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)

with tab2:
    st.markdown(f'**{best_or_worst} worstball**')
    st.write(worstball_output.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)