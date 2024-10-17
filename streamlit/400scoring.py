from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, datawrapper_table_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
datawrapper_table_css()
st.title("Scoring")

'---'
st.markdown("### Contents")
st.markdown('1. Average score by par')
st.markdown('2. Number of eagles, birdies etc.')
st.markdown('3. Most birdies etc. in a round')
st.markdown('4. Longest streaks')
'---'

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

'---'

st.subheader("Career Eagles, Birdies, Pars and Triple Bogey+")

# Calculate the stats
scoring_stats = score_type_stats()


chart_fields_all = [
    ['Eagles', 'Holes_per_Eagle'],
    ['Birdies', 'Holes_per_Birdie'],
    ['Pars_or_Better', 'Holes_per_Par_or_Better'],
    ['TBPs', 'Holes_per_TBP']
]

cnt_fields = len(chart_fields_all)

tab_labels = [chart_fields_all[i][0].replace("_", " ") for i in range(cnt_fields)]
tabs = st.tabs(tab_labels)

def format_dataframe_columns(df):
    # Create a copy of the dataframe to avoid modifying the original
    formatted_df = df.copy()
    formatted_df.iloc[:, 1] = formatted_df.iloc[:, 1].astype(int)
    formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}")
    formatted_df.columns = [col.replace('_', ' ') for col in formatted_df.columns]
    
    return formatted_df


for i, tab in enumerate(tabs):
    with tab:
        chart_fields = chart_fields_all[i]
        section_title = chart_fields[0].replace("_", " ")
        st.markdown(f"**Career {section_title}**")
        
        table_df = scoring_stats[['Player'] + chart_fields].sort_values(by=chart_fields, ascending=[False, True])
        table_df = format_dataframe_columns(table_df)
        st.write(table_df.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)

'---'

st.subheader('Most of each type of score in a single round')
max_by_round = max_scoretype_per_round()
st.write(max_by_round.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)

'---'

st.subheader('Longest Streaks by Player')

def calculate_multi_score_running_sum(df):
    # Sort the dataframe by Player and Career Count
    df_sorted = df.sort_values(['Player', 'Career Count'])
    
    # Define score types
    score_types = {
        'Pars_or_Better': lambda x: x <= 0,
        'Birdies': lambda x: x == -1,
        'TBPs': lambda x: x > 2
    }
    
    # Initialize running sum columns
    for score_type in score_types:
        df_sorted[f'RunningSum_{score_type}'] = 0
    
    # Group by Player and calculate the running sums
    def calc_running_sums(group):
        for score_type, condition in score_types.items():
            running_sum = 0
            for i, row in group.iterrows():
                if condition(row['GrossVP']):
                    running_sum += 1
                else:
                    running_sum = 0
                group.at[i, f'RunningSum_{score_type}'] = running_sum
        return group

    df_sorted = df_sorted.groupby('Player', group_keys=False).apply(calc_running_sums)
    
    # Merge the calculated RunningSum columns back to the original dataframe
    merge_columns = ['Player', 'Career Count'] + [f'RunningSum_{score_type}' for score_type in score_types]
    df = df.merge(df_sorted[merge_columns], on=['Player', 'Career Count'], how='left')
    
    return df



# Usage:
# df = calculate_multi_score_running_sum(df)

import pandas as pd

def summarize_multi_score_running_sum(df):
    # Ensure the RunningSum columns exist
    score_types = [ 'Birdies','Pars_or_Better', 'TBPs']
    for score_type in score_types:
        if f'RunningSum_{score_type}' not in df.columns:
            raise ValueError(f"RunningSum_{score_type} column not found. Please calculate the running sums first.")

    # Group by Player and get the maximum RunningSum for each score type
    summary = df.groupby('Player').agg({f'RunningSum_{score_type}': 'max' for score_type in score_types}).reset_index()
    
    # Rename the columns for clarity
    summary.columns = ['Player'] + score_types
    
    # Sort by Pars_or_Better (you can change this if you prefer a different sorting)
    summary = summary.sort_values('Pars_or_Better', ascending=False)
    
    return summary

# Usage:
# summary_df = summarize_multi_score_running_sum(df)
# summary_df.to_clipboard(index=False)
# print("Summary copied to clipboard. You can now paste it into a text editor or spreadsheet.")

all_data = load_all_data()
runsums = calculate_multi_score_running_sum(all_data)
streak_summary = summarize_multi_score_running_sum(runsums)
st.write(streak_summary.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)