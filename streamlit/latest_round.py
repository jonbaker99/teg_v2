import streamlit as st
import pandas as pd
from utils import get_ranked_teg_data, get_ranked_round_data, get_ranked_frontback_data, safe_ordinal, load_all_data
from utils import chosen_rd_context, chosen_teg_context, load_datawrapper_css
from make_charts import create_round_graph

# Initialize session state
if 'teg_r' not in st.session_state:
    st.session_state.teg_r = None
if 'rd_r' not in st.session_state:
    st.session_state.rd_r = None

load_datawrapper_css()

def reset_round_selection():
    st.session_state.teg_r = max_teg_r
    st.session_state.rd_r = max_rd_in_max_teg

st.subheader("Chosen Round in context")
st.markdown('Shows how latest or selected rounds and TEGs compare to other rounds')

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


df_round = get_ranked_round_data()
df_round = df_round.sort_values(by=['TEGNum','Round'])
max_teg_r = df_round.loc[df_round['TEGNum'].idxmax(), 'TEG']
max_rd_in_max_teg = df_round[df_round['TEG'] == max_teg_r]['Round'].max()

# Set initial values if not already set
if st.session_state.teg_r is None:
    st.session_state.teg_r = max_teg_r
if st.session_state.rd_r is None:
    st.session_state.rd_r = max_rd_in_max_teg

col1, col2, col3 = st.columns(3)

with col1:
    teg_options = list(df_round['TEG'].unique())
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

metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']
friendly_metrics = [inverted_name_mapping[metric] for metric in metrics]
all_data = load_all_data(exclude_incomplete_tegs=False)

tabs = st.tabs(friendly_metrics)


for tab, friendly_metric in zip(tabs, friendly_metrics):
    with tab:
        st.markdown(f"#### {friendly_metric}")
        metric = name_mapping.get(friendly_metric,friendly_metric)
        output = chosen_rd_context(df_round, teg_r, rd_r, metric).rename(columns={metric: friendly_metric})
        st.write(output.to_html(index=False, justify='left', classes='jb-table-test, datawrapper-table'), unsafe_allow_html=True)

        st.markdown(f"#### Cumulative {friendly_metric} through round")
        cum_metric = f'{metric} Cum Round'
        fig_rd = create_round_graph(all_data, chosen_teg=teg_r, chosen_round=rd_r, y_series=cum_metric,title=friendly_metric,y_axis_label=f'Cumulative {friendly_metric}')
        st.plotly_chart(fig_rd, use_container_width=True, config=dict({'displayModeBar': False}))