from utils import get_round_data, load_datawrapper_css, datawrapper_table
import streamlit as st

load_datawrapper_css()
st.title('Score swings vs. previous round')
st.caption("Shows the rounds with the biggest score differences to the player's previous round")

all_rd_data = get_round_data(ex_50 = True, ex_incomplete= False)
all_rd_data['TR'] = all_rd_data['TEGNum']*100 + all_rd_data['Round']

tegnum_options = ['All TEGs'] + sorted(all_rd_data['TEGNum'].unique().tolist(),reverse=True)
selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

# Filter data based on TEGNum selection
if selected_tegnum != 'All TEGs':
    selected_tegnum = int(selected_tegnum)
    filtered_data = all_rd_data[all_rd_data['TEGNum'] == selected_tegnum]
else:
    filtered_data = all_rd_data

top_n = 10

col1, col2 = st.columns(2)

with col1:
    over_tegs = st.radio("Include changes across TEGs?", ('Yes', 'No'), horizontal=True,  index=1)

with col2:
    all_or_n = st.radio("Rounds to show:", ('All', f'Top {top_n}'), horizontal=True,  index=1)

grouper = ['Pl','TEG'] if over_tegs == 'No' else ['Pl']
rd_data = filtered_data

rd_data.sort_values(['Pl', 'TR'], inplace=True)
rd_data['diff'] = (rd_data.groupby(grouper)['Sc'].diff().values)
rd_data['prev_Sc'] = rd_data.groupby(grouper)['Sc'].shift()
rd_data.dropna(subset=['diff'], inplace=True)
# rd_data['diff_abs'] = rd_data['diff'].abs()   
# rd_data.sort_values(['diff_abs'],inplace=True, ascending=False)
rd_data[['Sc','prev_Sc','diff']] = rd_data[['Sc','prev_Sc','diff']].astype(int)
rd_data = rd_data[['Pl','TEG','Round','Course','Year','Sc','prev_Sc','diff']]

rd_data.rename(columns={
    'diff': 'Change',
    'prev_Sc': 'Previous Rd'
}, inplace=True)

rd_data_best = rd_data.sort_values(by = 'Change', ascending= True)
rd_data_worst = rd_data.sort_values(by = 'Change', ascending= False)

if not(all_or_n == 'All'):
    rd_data_best = rd_data_best.nsmallest(top_n, 'Change', keep='all')
    rd_data_worst = rd_data_worst.nlargest(top_n, 'Change', keep='all')

tab1, tab2  = st.tabs(["Biggest improvements", "Biggest worsenings"])

with tab1:
    st.markdown('Best performance vs. previous round')
    datawrapper_table(rd_data_best, css_classes='full-width')

with tab2:
    st.markdown('Worst performance vs. previous round')
    datawrapper_table(rd_data_worst, css_classes='full-width')



# rd_data = filtered_data

# rd_data.sort_values(['Pl', 'TR'], inplace=True)
# rd_data['diff'] = (rd_data.groupby('Pl')['Sc'].diff().values)
# rd_data['prev_Sc'] = rd_data.groupby('Pl')['Sc'].shift()
# rd_data.dropna(subset=['diff'], inplace=True)
# rd_data['diff_abs'] = rd_data['diff'].abs()   
# rd_data.sort_values(['diff_abs'],inplace=True, ascending=False)
# rd_data[['Sc','prev_Sc','diff']] = rd_data[['Sc','prev_Sc','diff']].astype(int)
# rd_data_output = rd_data[['Pl','TEG','Round','Course','Year','Sc','prev_Sc','diff']]

# datawrapper_table(rd_data_output)

# === NAVIGATION LINKS ===
from utils import add_navigation_links
add_navigation_links(__file__)

# rd_data = filtered_data

# rd_data.sort_values(['Pl', 'TR'], inplace=True)

# rd_data['diff'] = rd_data.groupby(['Pl', 'TEG'])['Sc'].diff().values
# rd_data['prev_Sc'] = rd_data.groupby(['Pl', 'TEG'])['Sc'].shift()

# rd_data.dropna(subset=['diff'], inplace=True)
# rd_data['diff_abs'] = rd_data['diff'].abs()   
# rd_data.sort_values(['diff_abs'],inplace=True, ascending=False)
# rd_data[['Sc','prev_Sc','diff']] = rd_data[['Sc','prev_Sc','diff']].astype(int)
# rd_data_output = rd_data[['Pl','TEG','Round','Course','Year','Sc','prev_Sc','diff']]

# datawrapper_table(rd_data_output)

# === NAVIGATION LINKS ===
from utils import add_navigation_links
add_navigation_links(__file__)
