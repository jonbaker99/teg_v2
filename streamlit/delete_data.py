import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shutil
from utils import ALL_SCORES_PATH, PARQUET_FILE, CSV_OUTPUT_FILE, BASE_DIR

# Initialize session state variables
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.scores_df = None
    st.session_state.data_df = None
    st.session_state.parquet_df = None
    st.session_state.selected_teg = None
    st.session_state.selected_rounds = []
    st.session_state.preview_clicked = False
    st.session_state.confirm_clicked = False

def load_data():
    scores_df = pd.read_csv(ALL_SCORES_PATH)
    data_df = pd.read_csv(CSV_OUTPUT_FILE)
    parquet_df = pd.read_parquet(PARQUET_FILE)
    return scores_df, data_df, parquet_df

def save_data(scores_df, data_df, parquet_df):
    scores_df.to_csv(ALL_SCORES_PATH, index=False)
    data_df.to_csv(CSV_OUTPUT_FILE, index=False)
    parquet_df.to_parquet(PARQUET_FILE, index=False)

def create_backup():
    backup_folder = BASE_DIR / 'data' / 'backups'
    backup_folder.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    scores_backup = backup_folder / f'all_scores_backup_{timestamp}.csv'
    shutil.copy(ALL_SCORES_PATH, scores_backup)
    
    parquet_backup = backup_folder / f'all_data_backup_{timestamp}.parquet'
    shutil.copy(PARQUET_FILE, parquet_backup)
    
    return scores_backup, parquet_backup

def perform_deletion(scores_df, data_df, parquet_df, selected_teg, selected_rounds):
    scores_df = scores_df[~((scores_df['TEGNum'] == selected_teg) & (scores_df['Round'].isin(selected_rounds)))]
    data_df = data_df[~((data_df['TEGNum'] == selected_teg) & (data_df['Round'].isin(selected_rounds)))]
    parquet_df = parquet_df[~((parquet_df['TEGNum'] == selected_teg) & (parquet_df['Round'].isin(selected_rounds)))]

    save_data(scores_df, data_df, parquet_df)
    return scores_df, data_df, parquet_df

def delete_data_page():
    st.title("Delete Tournament Data")

    if not st.session_state.data_loaded:
        st.session_state.scores_df, st.session_state.data_df, st.session_state.parquet_df = load_data()
        st.session_state.data_loaded = True

    teg_nums = sorted(st.session_state.scores_df['TEGNum'].unique(), reverse=True)
    teg_nums = [''] + teg_nums  # Add an empty option at the beginning
    selected_teg = st.selectbox("Select TEGNum to delete data for:", teg_nums, index=0)
    st.session_state.selected_teg = selected_teg if selected_teg != '' else None

    rounds = sorted(st.session_state.scores_df[st.session_state.scores_df['TEGNum'] == st.session_state.selected_teg]['Round'].unique())
    st.write("Select Rounds to delete:")
    st.session_state.selected_rounds = [round for round in rounds if st.checkbox(f"Round {round}", key=f"round_{round}")]

    if st.button("Preview Deletion"):
        st.session_state.preview_clicked = True

    if st.session_state.preview_clicked:
        preview_deletion()

def preview_deletion():
    st.subheader("Deletion Preview")
    st.write(f"TEG: {st.session_state.selected_teg}")
    st.write(f"Rounds: {', '.join(map(str, st.session_state.selected_rounds))}")

    scores_to_delete = st.session_state.scores_df[
        (st.session_state.scores_df['TEGNum'] == st.session_state.selected_teg) & 
        (st.session_state.scores_df['Round'].isin(st.session_state.selected_rounds))
    ]
    data_to_delete = st.session_state.data_df[
        (st.session_state.data_df['TEGNum'] == st.session_state.selected_teg) & 
        (st.session_state.data_df['Round'].isin(st.session_state.selected_rounds))
    ]
    parquet_to_delete = st.session_state.parquet_df[
        (st.session_state.parquet_df['TEGNum'] == st.session_state.selected_teg) & 
        (st.session_state.parquet_df['Round'].isin(st.session_state.selected_rounds))
    ]

    st.write(f"Rows to be deleted from all_scores.csv: {len(scores_to_delete)}")
    st.write(f"Rows to be deleted from all_data.csv: {len(data_to_delete)}")
    st.write(f"Rows to be deleted from all_data.parquet: {len(parquet_to_delete)}")

    st.warning("Warning: This action will permanently delete the selected data.")
    if st.button("Confirm Deletion"):
        st.session_state.confirm_clicked = True

    if st.session_state.confirm_clicked:
        confirm_deletion()

def confirm_deletion():
    st.warning("Are you absolutely sure you want to delete this data? This action cannot be undone.")
    if st.button("Yes, I'm sure. Delete the data."):
        scores_backup, parquet_backup = create_backup()
        st.info(f"Backups created: \n{scores_backup}\n{parquet_backup}")
        
        st.session_state.scores_df, st.session_state.data_df, st.session_state.parquet_df = perform_deletion(
            st.session_state.scores_df, 
            st.session_state.data_df, 
            st.session_state.parquet_df, 
            st.session_state.selected_teg, 
            st.session_state.selected_rounds
        )
        
        st.success("Data has been successfully deleted and files have been updated.")
        st.session_state.preview_clicked = False
        st.session_state.confirm_clicked = False

delete_data_page()