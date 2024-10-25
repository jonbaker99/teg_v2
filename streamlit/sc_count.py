import streamlit as st
import pandas as pd
from utils import load_all_data, datawrapper_table_css, datawrapper_table, format_vs_par
import plotly.express as px

all_data = load_all_data(exclude_incomplete_tegs = False)
datawrapper_table_css()

st.title('Count of score by player')


tegnum_options = ['All TEGs'] + sorted(all_data['TEGNum'].unique().tolist(),reverse=True)
selected_tegnum = st.selectbox('Filter by TEG (optional)', tegnum_options, index=0)

par_options = ['All holes'] + sorted(all_data['PAR'].unique().tolist())
selected_par = st.selectbox('Filter by par (optional)', par_options, index=0)

#selected_tegnum = 'All TEGs'

# Filter data based on TEGNum selection
if selected_tegnum != 'All TEGs':
    selected_tegnum = int(selected_tegnum)
    filtered_data_teg = all_data[all_data['TEGNum'] == selected_tegnum]
    teg_desc = f'TEG {selected_tegnum} only'
else:
    filtered_data_teg = all_data
    teg_desc = 'All TEGs'

# Filter data based on par selection
if selected_par != 'All holes':
    selected_par = int(selected_par)
    filtered_data = filtered_data_teg[all_data['PAR'] == selected_par]
    par_desc = f'Par {selected_par}s only'
else:
    filtered_data = filtered_data_teg
    par_desc = 'All holes'

def count_by_pl(df = all_data, field = 'GrossVP'):

    summary = df.groupby([field, 'Pl']).size().unstack(fill_value=0)
    
    # Sort the index (GrossVP) in descending order
    summary = summary.sort_index(ascending=True)
    
    # Optional: Sort columns (players) alphabetically
    summary = summary.sort_index(axis=1)
    
    return summary
    

count_gvp = count_by_pl(filtered_data, 'GrossVP')
count_sc = count_by_pl(filtered_data, 'Sc')


def make_percent_plot(df = None):

    # Set the first column (whatever it may be) as the index
    df.set_index(df.columns[0], inplace=True)

    # Calculate % of total for each column
    df_percentage = df.div(df.sum(axis=0), axis=1) #* 100  # Calculate percentages

    # Prepare the Plotly figure & customise
    fig = px.bar(df_percentage, barmode='group') #, text_auto=True)
    fig.update_layout(
        title="% of total | " + teg_desc + ' | ' +par_desc,
        xaxis_title=df.index.name,  # Use the name of the index (vs Par)
        yaxis_title="% of Total",
        legend_title="Pl",
        bargap=0.3,
        bargroupgap=0.0,    
    )
    fig.layout.xaxis.fixedrange = True # remove ability to zoom on x
    fig.layout.yaxis.fixedrange = True # remove ability to zoom on y

    return fig


tab1, tab2  = st.tabs(["Scores", "Scores vs Par"])

with tab1:
    st.markdown('### Count of gross score by player')
    st.caption(teg_desc + ' | ' +par_desc)
    # st.dataframe(count_sc, height = len(count_sc) * 35 + 38)
    count_sc = count_sc.reset_index()
    count_sc.columns.name = None
    count_sc['Sc'] = count_sc['Sc'].astype(int)
    count_sc = count_sc.rename(columns={'Sc': 'Score'})
    datawrapper_table(count_sc)
    st.plotly_chart(make_percent_plot(count_sc))


with tab2:
    st.markdown('### Count of Gross vs Par by player')
    st.caption(teg_desc + ' | ' +par_desc)
    # st.dataframe(count_gvp, height = len(count_gvp) * 35 + 38)
    count_gvp = count_gvp.reset_index()
    count_gvp['GrossVP'] = count_gvp['GrossVP'].apply(format_vs_par)
    count_gvp = count_gvp.rename(columns={'GrossVP': 'vs Par'})
    count_gvp.columns.name = None
    datawrapper_table(count_gvp)
    count_gvp.loc[count_gvp['vs Par'] == '=', 'vs Par'] = 0
    st.plotly_chart(make_percent_plot(count_gvp))