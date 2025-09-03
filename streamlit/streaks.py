from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, load_datawrapper_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
load_datawrapper_css()
st.title('Longest Streaks')

def calculate_multi_score_running_sum(df):
    # Sort the dataframe by Player and Career Count
    df_sorted = df.sort_values(['Player', 'Career Count'])
    
    # Define score types
    score_types = {
        'Pars_or_Better': lambda x: x <= 0,
        'Birdies': lambda x: x == -1,
        'TBPs': lambda x: x > 2,
        #'No TBP': lambda x: x < 3
        'Bogey or better': lambda x: x < 2
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
    score_types = [ 'Birdies','Pars_or_Better', 'TBPs','Bogey or better']
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

all_data = load_all_data(exclude_teg_50=True)
runsums = calculate_multi_score_running_sum(all_data)
streak_summary = summarize_multi_score_running_sum(runsums)
st.write(streak_summary.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)