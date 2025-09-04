from utils import get_round_data, load_datawrapper_css, datawrapper_table
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

load_datawrapper_css()
st.title('Course averages and records')

all_rd_data = get_round_data(ex_50 = True, ex_incomplete= False)
rd_data = all_rd_data

# Number of rounds at each course
course_count = (
    rd_data[['Course', 'TEG', 'Round']]
    .drop_duplicates()  # Ensure unique combinations of 'Course', 'TEG', 'Round'
    .groupby('Course')  # Group by 'Course'
    .size()  # Count the number of unique 'TEG', 'Round' per 'Course'
    .reset_index(name='Count')  # Reset index and name the count column
    .sort_values(by='Count', ascending=False)  # Sort by 'Count'
)


def by_course(df, aggfunc = 'mean'):
    round_to = 1 if aggfunc == 'mean' else 0

    course_count_df = (
        df[['Course', 'TEG', 'Round']]
        .drop_duplicates()  # Ensure unique combinations of 'Course', 'TEG', 'Round'
        .groupby('Course')  # Group by 'Course'
        .size()  # Count the number of unique 'TEG', 'Round' per 'Course'
        .reset_index(name='Count')  # Reset index and name the count column
        .sort_values(by='Count', ascending=False)  # Sort by 'Count'
    )

    #print(course_count)


    rd_data = df.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc=aggfunc)
    rd_data.loc[:, rd_data.columns != 'Course'] = rd_data.loc[:, rd_data.columns != 'Course'].round(round_to)
    rd_total = df.groupby('Course').agg({'GrossVP': aggfunc})
    # if aggfunc == 'mean':
        #rd_data.loc[:, rd_data.columns != 'Round'] = rd_data.loc[:, rd_data.columns != 'Course'].round(round_to)
    #else:
        #rd_data.loc[:, rd_data.columns != 'Round'] = rd_data.loc[:, rd_data.columns != 'Course'].apply(lambda x: int(x) if pd.notna(x) else x)
    
    rd_data['Total'] = rd_total
    rd_data = rd_data.reset_index()
    rd_data.columns.name = None

    def format_number(x):
        if isinstance(x, str):  # Check if x is already a string
            return x  # Return the string as is
        elif pd.isna(x):  # Check if x is NaN
            return "-"  # You can return any placeholder or message for NaN
        elif x == 0:
            return "="  # Return '=' for zero
        elif round_to == 0:
            return f"{int(x):+d}"  # Return integer if round_to is 0
        else:
            return f"{x:+.{round_to}f}"  # Return floating point formatted string

    rd_data = rd_data.applymap(format_number)
    rd_data = pd.merge(rd_data, course_count_df, on='Course').sort_values(by = 'Count', ascending= False).drop(columns=['Count'])

    return(rd_data)

mean_rd = by_course(rd_data, 'mean')
min_rd = by_course(rd_data, 'min')
max_rd = by_course(rd_data, 'max')

course_count['Ave'] = mean_rd['Total']
course_count['Record'] = min_rd['Total']
course_count['Worst'] = max_rd['Total']
course_count = course_count.rename(columns={'Count':'Rounds'})
tab1, tab2, tab3, tab4  = st.tabs(["Summary by course","Course average", "Best Rounds", "Worst Rounds"])

with tab1:
    datawrapper_table(course_count, css_classes='full-width')

with tab2:
    datawrapper_table(mean_rd, css_classes='full-width')

with tab3:
    datawrapper_table(min_rd, css_classes='full-width')

with tab4:
    datawrapper_table(max_rd, css_classes='full-width')
