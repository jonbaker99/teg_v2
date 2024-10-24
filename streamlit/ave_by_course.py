from utils import get_round_data, datawrapper_table_css, datawrapper_table
import streamlit as st
import pandas as pd, altair as alt
import numpy as np

#st.set_page_config(page_title="TEG Scoring")
datawrapper_table_css()
st.title('Course averages and records')

all_rd_data = get_round_data(ex_50 = True, ex_incomplete= False)
rd_data = all_rd_data

def by_course(df, aggfunc = 'mean'):
    round_to = 1 if aggfunc == 'mean' else 0
    rd_data = df.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc=aggfunc)
    rd_data.loc[:, rd_data.columns != 'Course'] = rd_data.loc[:, rd_data.columns != 'Course'].round(round_to)
    rd_total = df.groupby('Course').agg({'GrossVP': aggfunc})
    # if aggfunc == 'mean':
        #rd_data.loc[:, rd_data.columns != 'Round'] = rd_data.loc[:, rd_data.columns != 'Course'].round(round_to)
    #else:
        #rd_data.loc[:, rd_data.columns != 'Round'] = rd_data.loc[:, rd_data.columns != 'Course'].apply(lambda x: int(x) if pd.notna(x) else x)
    
    rd_data['Total'] = rd_total
    rd_data = rd_data.reset_index()

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
    return(rd_data)

mean_rd = by_course(rd_data, 'mean')
min_rd = by_course(rd_data, 'min')
max_rd = by_course(rd_data, 'max')

tab1, tab2, tab3  = st.tabs(["Course average", "Best Rounds", "Worst Rounds"])

with tab1:
    datawrapper_table(mean_rd)

with tab2:
    datawrapper_table(min_rd)

with tab3:
    datawrapper_table(max_rd)
