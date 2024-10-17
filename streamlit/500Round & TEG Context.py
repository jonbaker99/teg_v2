import streamlit as st
import pandas as pd
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, safe_ordinal
from utils import chosen_rd_context, chosen_teg_context, datawrapper_table_css

# Initialize session state
if 'teg_r' not in st.session_state:
    st.session_state.teg_r = None
if 'rd_r' not in st.session_state:
    st.session_state.rd_r = None
if 'teg_t' not in st.session_state:
    st.session_state.teg_t = None

datawrapper_table_css()

def reset_round_selection():
    st.session_state.teg_r = max_teg_r
    st.session_state.rd_r = max_rd_in_max_teg

def reset_teg_selection():
    st.session_state.teg_t = max_teg_t

st.subheader("Round and TEG context")
st.markdown('Shows how latest or selected rounds and TEGs compare to other rounds')

name_mapping = {
    'Gross vs Par': 'GrossVP',
    'Score': 'Sc',
    'Net vs Par': 'NetVP',
    'Stableford': 'Stableford'
}
inverted_name_mapping = {v: k for k, v in name_mapping.items()}

tab1, tab2 = st.tabs(["Chosen Round","Chosen TEG"])

with tab1:
    df_round = get_ranked_round_data()
    max_teg_r = df_round.loc[df_round['TEGNum'].idxmax(), 'TEG']
    max_rd_in_max_teg = df_round[df_round['TEG'] == max_teg_r]['Round'].max()

    # Set initial values if not already set
    if st.session_state.teg_r is None:
        st.session_state.teg_r = max_teg_r
    if st.session_state.rd_r is None:
        st.session_state.rd_r = max_rd_in_max_teg

    col1, col2, col3 = st.columns(3)

    with col1:
        teg_options = sorted(df_round['TEG'].unique())
        teg_index = teg_options.index(st.session_state.teg_r)
        teg_r = st.selectbox("Select TEG (Round)", options=teg_options, index=teg_index, key='teg_r_select')
        st.session_state.teg_r = teg_r

    with col2:
        rd_options = sorted(df_round[df_round['TEG'] == teg_r]['Round'].unique())
        rd_index = rd_options.index(st.session_state.rd_r) if st.session_state.rd_r in rd_options else 0
        rd_r = st.selectbox("Select Round", options=rd_options, index=rd_index, key='rd_r_select')
        st.session_state.rd_r = rd_r

    with col3:
        st.button("Latest Round", on_click=reset_round_selection)

    # Display round context tables
    for metric in ['Sc', 'Stableford', 'GrossVP', 'NetVP']:
        '---'
        friendly_metric = inverted_name_mapping.get(metric,metric)
        st.markdown(f"#### {friendly_metric}")
        output = chosen_rd_context(df_round, teg_r, rd_r, metric)
        st.write(output.to_html(index=False, justify='left', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)

with tab2:
    df_teg = get_ranked_teg_data()
    max_teg_t = df_teg.loc[df_teg['TEGNum'].idxmax(), 'TEG']

    # Set initial value if not already set
    if st.session_state.teg_t is None:
        st.session_state.teg_t = max_teg_t

    col1, col2 = st.columns(2)

    with col1:
        teg_options = sorted(df_teg['TEG'].unique())
        teg_index = teg_options.index(st.session_state.teg_t)
        teg_t = st.selectbox("Select TEG", options=teg_options, index=teg_index, key='teg_t_select')
        st.session_state.teg_t = teg_t

    with col2:
        st.button("Latest TEG", on_click=reset_teg_selection)

    # Display TEG context tables
    for metric in ['Sc', 'Stableford', 'GrossVP', 'NetVP']:
        '---'
        friendly_metric = inverted_name_mapping.get(metric,metric)
        st.markdown(f"#### {friendly_metric}")
        output = chosen_teg_context(df_teg, teg_t, metric)
        st.write(output.to_html(index=False, justify='left', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)