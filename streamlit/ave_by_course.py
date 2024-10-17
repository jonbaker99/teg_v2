from utils import score_type_stats, load_all_data, apply_score_types, max_scoretype_per_round, format_vs_par, datawrapper_table_css
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
datawrapper_table_css()
st.title('Average score by Course')

all_data = load_all_data(exclude_incomplete_tegs=False)
# avg_grossvp = all_data.groupby(['Player', 'Course'])['GrossVP'].mean().unstack(fill_value=0)
# avg_grossvp['Total'] = all_data.groupby('Player')['GrossVP'].mean()
# avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
# avg_grossvp = avg_grossvp.round(2)


# def format_value(value):
#     if value > 0:
#         return f"+{value:.2f}"
#     elif value < 0:
#         return f"{value:.2f}"
#     else:
#         return "="

# for column in avg_grossvp.columns:
#     avg_grossvp[column] = avg_grossvp[column].apply(format_value)

# avg_grossvp.reset_index(inplace=True)
# avg_grossvp.columns.name = None
# avg_grossvp.columns = ['Player'] + [f'Par {col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]

# st.write(avg_grossvp.to_html(classes='dataframe, datawrapper-table', index=False, justify='left'), unsafe_allow_html=True)

# avg_grossvp = all_data.groupby(['Player', 'Course'])['GrossVP'].mean().unstack(fill_value=0)
# avg_grossvp['Total'] = all_data.groupby('Course')['GrossVP'].mean()
# avg_grossvp = avg_grossvp.sort_values('Total', ascending=True)
# avg_grossvp = avg_grossvp.round(1)


# def format_value(value):
#     if value > 0:
#         return f"+{value:.2f}"
#     elif value < 0:
#         return f"{value:.2f}"
#     else:
#         return "-"

# for column in avg_grossvp.columns:
#     avg_grossvp[column] = avg_grossvp[column].apply(format_value)

# avg_grossvp.reset_index(inplace=True)
# avg_grossvp.columns.name = None
# avg_grossvp.columns = ['Course'] + [f'{col}' if col != 'Total' else col for col in avg_grossvp.columns[1:]]

# st.write(avg_grossvp.to_html(classes='dataframe, datawrapper-table', index=False, justify='left'), unsafe_allow_html=True)


# # Step 1: Group by Course and Player to calculate the mean GrossVP for each player in each course
# summary = all_data.groupby(['Course', 'Pl'])['GrossVP'].mean().unstack(fill_value=0)

# # Step 2: Add a 'Total' row for each course, calculating the average GrossVP across all players
# summary['Total'] = summary.mean(axis=1)

# # Step 3: Transpose the DataFrame so that Courses are rows and Players are columns
# summary_transposed = summary.T

# # Step 4: Add a 'Total' column for each player (mean across all courses)
# summary_transposed['Total'] = summary_transposed.mean(axis=1)

# # Step 5: Convert the transposed DataFrame to an HTML table
# html_table = summary_transposed.to_html(classes='dataframe, datawrapper-table', index=True, justify='left')

# # Step 6: Display the table in Streamlit
# st.write(html_table, unsafe_allow_html=True)


'---'


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
        return f"{x:.1f}"
    else:
        return str(x)

# Apply the formatting function to the entire DataFrame
formatted_summary = summary.applymap(format_number)

# Display the table using Streamlit
st.dataframe(formatted_summary,use_container_width=True,height=35*len(summary)+38)
