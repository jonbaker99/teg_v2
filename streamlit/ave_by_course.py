from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, datawrapper_table_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
datawrapper_table_css()
st.title('Average score by Course')

all_data = load_all_data(exclude_incomplete_tegs=False)

st.markdown(
    """
    <style>
    [data-testid="stElementToolbar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Calculate the mean of GrossVP for each player in each course
summary = all_data.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc='mean')

# Multiply all values by 18
summary = summary * 18

# Calculate the total column based on the underlying dataset
total = all_data.groupby('Course')['GrossVP'].mean() * 18
summary['Total'] = total

# Sort the DataFrame by the 'Total' column in descending order
summary = summary.sort_values('Total', ascending=False)

# Reset the index to make 'Course' a column
summary = summary.reset_index()

# Add a Rank column
summary['Rank'] = range(1, len(summary) + 1)

# Set Rank as the index
summary = summary.set_index('Rank')

# Reorder columns to put Course first
columns = ['Course'] + [col for col in summary.columns if col not in ['Course', 'Rank']]
summary = summary[columns]

# Function to format numbers with 1 decimal place and display NaN as '-'
def format_number(x):
    if pd.isna(x):
        return '-'
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        return f"{x:+.1f}"
    else:
        return str(x)

# Apply the formatting function to the entire DataFrame
formatted_summary = summary.applymap(format_number)

tab1, tab2  = st.tabs(["Totals only", "By Player"])

with tab2:

    # Display the table using Streamlit
    st.dataframe(formatted_summary,use_container_width=True,height=35*len(summary)+38)

with tab1:
    summary = summary[['Course','Total']]#.reset_index()
    summary['Total'] = summary['Total'].apply(format_number)
    st.dataframe(summary,use_container_width=True,height=35*len(summary)+38)
