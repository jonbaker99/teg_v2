from utils import get_ranked_teg_data, get_best, get_ranked_round_data, get_ranked_frontback_data, create_stat_section
from utils import get_complete_teg_data, get_round_data, get_9_data, get_worst
import streamlit as st
import pandas as pd

#st.set_page_config(page_title="TEG Records", page_icon="⛳")
st.title("TEG Worsts")

'---'
st.markdown("### Contents")
st.markdown('1. Worst TEGs')
st.markdown('2. Worst Rounds')
st.markdown('3. Worst 9s')
'---'

# Custom CSS
st.markdown("""
    <style>

    div[data-testid="column"] {
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 20px;
        height: 100%;
    }
    # div[data-testid="column"]:first-child {
    #     margin-right: 20px;
    #     border-right: 1px solid #ccc;
    #     padding-right: 40px;
    # }
    # div[data-testid="column"]:last-child {
    #     margin-left: 20px;
    #     padding-left: 40px;
    # }
    .stat-section {
        margin-bottom: 20px;
        background-color: rgb(240, 242, 246);
        padding: 20px;
        margin: 5px;
    }
    .stat-section h2 {
        margin-bottom: 5px;
        font-size: 22px;
        line-height: 1.0;
        color: #333;
        padding: 0;
    }
    .stat-section h2 .title {
        font-weight: normal;
    }
    .stat-section h2 .value {
        font-weight: bold;
    }
    .stat-details {
        font-size: 16px;
        color: #999;
        line-height: 1.4;
    }
    .stat-details .Player {
    #    font-weight: bold;
        color: #666;
    }
    .stat-details .Course {
    #    font-style: italic;
    }
    .stat-details .Year {
    #    color: #999;
    }
    </style>
    """, unsafe_allow_html=True)


MEASURE_TITLES = {
    'Sc': "Worst Score",
    'GrossVP': "Worst Gross",
    'NetVP': "Worst Net",
    'Stableford': "Worst Stableford"
}

def format_value(value, measure):
    return f"{int(value):+}" if measure in ['GrossVP', 'NetVP'] else str(int(value))

def prepare_df(best_records, record_type):
    df = best_records.copy()
    df['Year'] = df['Year'].astype(str)
    
    if record_type in ['round', 'frontback']:
        df['Round'] = 'R' + df['Round'].astype(str)
        df['TEG_Round'] = df['TEG'] + ', ' + df['Round']
        
        if record_type == 'frontback':
            df['TEG_Round'] += ' ' + df['FrontBack'] + ' 9'
        
        df = df[['Player', 'Course', 'TEG_Round', 'Year']]
    else:  # TEG
        df = df[['Player', 'TEG', 'Year']]
    
    return df


#tegs_ranked = get_ranked_teg_data()
teg = get_complete_teg_data()
teg = teg[teg['TEGNum']!=2]
st.subheader('Worst TEGs')

for measure in ['GrossVP', 'NetVP', 'Stableford']:
    worst_records = get_worst(teg, measure_to_use=measure, top_n=1)
    title = MEASURE_TITLES[measure]
    value = format_value(worst_records[measure].iloc[0], measure)
    df = prepare_df(worst_records, 'teg')
    st.markdown(create_stat_section(title, value, df, "| "), unsafe_allow_html=True)
st.caption('Excludes TEG 2')
'---'
#rounds_ranked = get_ranked_round_data()
rds = get_round_data()
st.subheader('Worst Rounds')
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    worst_records = get_worst(rds, measure_to_use=measure, top_n=1)
    title = MEASURE_TITLES[measure]
    value = format_value(worst_records[measure].iloc[0], measure)
    df = prepare_df(worst_records, 'round')
    st.markdown(create_stat_section(title, value, df, "| "), unsafe_allow_html=True)

'---'
frontback = get_9_data()
#frontback_ranked = get_ranked_frontback_data()
st.subheader('Worst 9s')
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    worst_records = get_worst(frontback, measure_to_use=measure, top_n=1)
    title = MEASURE_TITLES[measure]
    value = format_value(worst_records[measure].iloc[0], measure)
    df = prepare_df(worst_records, 'frontback')
    st.markdown(create_stat_section(title, value, df, "| "), unsafe_allow_html=True)