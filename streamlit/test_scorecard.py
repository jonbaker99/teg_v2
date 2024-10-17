import pandas as pd
import streamlit as st
from utils import load_all_data

TEG = "TEG 16"
Rd = 4

all_data = load_all_data()
rd_data = all_data[(all_data['TEG'] == TEG) & (all_data['Round'] == Rd)]


rd_scores = rd_data[['Pl','Sc']]


data_df = pd.DataFrame(
    {
        "sales": [
            [0, 4, 26, 80, 100, 40],
            [80, 20, 80, 35, 40, 100],
            [10, 20, 80, 80, 70, 0],
            [10, 100, 20, 100, 30, 100],
        ],
    }
)

st.data_editor(
    data_df,
    column_config={
        "sales": st.column_config.ListColumn(
            "Sales (last 6 months)",
            help="The sales volume in the last 6 months",
            width="medium",
        ),
    },
    hide_index=True,
)

rd_scores_grouped = rd_data.groupby('Pl')['Sc'].apply(list).reset_index()

rd_scores_list = rd_scores_grouped['Sc'].tolist()

data_df = rd_scores_list

st.dataframe(
    data_df,
    column_config={
        "Sc": st.column_config.ListColumn(
            "Scores in the round",
            help="The scores",
            width="wide",
        ),
    },
    hide_index=True,
)