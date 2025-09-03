import streamlit as st
import pandas as pd
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, safe_ordinal
from utils import chosen_rd_context, chosen_teg_context, load_datawrapper_css

# Initialize session state
if 'teg_t' not in st.session_state:
    st.session_state.teg_t = None

load_datawrapper_css()


def reset_teg_selection():
    st.session_state.teg_t = max_teg_t

st.subheader("TEG context")
st.markdown('Shows how latest or selected TEG compares to other TEGs')

name_mapping = {
    'Gross vs Par': 'GrossVP',
    'Score': 'Sc',
    'Net vs Par': 'NetVP',
    'Stableford': 'Stableford'
}
inverted_name_mapping = {v: k for k, v in name_mapping.items()}

# metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP'] #in order they'll appear
# metrics_friendly = [inverted_name_mapping[metric] for metric in metrics]

# cnt_fields = len(metrics)

# tab_labels = [metrics_friendly[i][0] for i in range(cnt_fields)] #for use later
# tabs = st.tabs(tab_labels)



df_teg = get_ranked_teg_data().sort_values(by='TEGNum')
max_teg_t = df_teg.loc[df_teg['TEGNum'].idxmax(), 'TEG']

# Set initial value if not already set
if st.session_state.teg_t is None:
    st.session_state.teg_t = max_teg_t

col1, col2 = st.columns(2)

with col1:
    teg_options = list(df_teg['TEG'].unique())
    teg_index = teg_options.index(st.session_state.teg_t)
    teg_t = st.selectbox("Select TEG", options=teg_options, index=teg_index, key='teg_t_select')
    st.session_state.teg_t = teg_t

with col2:
    st.button("Latest TEG", on_click=reset_teg_selection)

metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']
friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]

tabs = st.tabs(friendly_metrics)

for tab, friendly_metric in zip(tabs, friendly_metrics):
    with tab:
        st.markdown(f"#### {friendly_metric}")
        metric = name_mapping.get(friendly_metric,friendly_metric)
        output = chosen_teg_context(df_teg, teg_t, metric).rename(columns={metric: friendly_metric})
        st.write(output.to_html(index=False, justify='left', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)
