"""
Data input utilities for TEG data analysis.

Functions for loading external data from Google Sheets and preparing handicap data.
These functions handle data ingestion from external sources.
"""

import os
import pandas as pd
import streamlit as st
import logging
from google.oauth2.service_account import Credentials
import gspread

# Import dependencies from other modules
from utils_core_io import read_file

# Configure logging
logger = logging.getLogger(__name__)

def get_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load data from a specified Google Sheet and worksheet using credentials from 
    Railway environment variables or Streamlit secrets.
    
    Parameters:
        sheet_name (str): Name of the Google Sheet
        worksheet_name (str): Name of the worksheet within the sheet
        
    Returns:
        pd.DataFrame: Data from the Google Sheet
        
    Purpose:
        Loads golf tournament data from Google Sheets for processing.
        Used by data update workflows to import new tournament results.
    """
    logger.info(f"Fetching data from Google Sheet: {sheet_name}, Worksheet: {worksheet_name}")
    
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    try:
        # Try Railway environment variables first, fallback to st.secrets for local development
        if os.getenv('GOOGLE_TYPE'):
            # Railway environment variables
            service_account_info = {
                "type": os.getenv('GOOGLE_TYPE'),
                "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n') if os.getenv('GOOGLE_PRIVATE_KEY') else None,
                "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
                "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
                "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
                "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL')
            }
            creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
        else:
            # Local development using Streamlit secrets
            service_account_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)

        client = gspread.authorize(creds)
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        logger.info(f"Successfully loaded {len(df)} rows from {sheet_name}")
        return df

    except Exception as e:
        logger.error(f"Error accessing Google Sheets: {e}")
        st.error(f"Could not load data from Google Sheet: {sheet_name}")
        return pd.DataFrame()

@st.cache_data
def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:
    """
    Load and prepare handicap data from a CSV file.

    Parameters:
        file_path (str): Path to the handicap CSV file.

    Returns:
        pd.DataFrame: Melted and cleaned handicap DataFrame.
        
    Purpose:
        Loads and processes handicap data for tournament calculations.
        Cached for performance as handicaps don't change frequently.
    """
    logger.info(f"Loading handicap data from {file_path}")
    try:
        hc_lookup = read_file(file_path)
    except Exception as e:
        logger.error(f"File not found: {file_path}")
        raise

    # Check if data is loaded
    if hc_lookup.empty:
        logger.warning("Handicap lookup table is empty.")
        return pd.DataFrame()

    # Melt the DataFrame to long format
    hc_long = pd.melt(
        hc_lookup, 
        id_vars=['TEG'], 
        var_name='Player', 
        value_name='Handicap'
    )

    # Remove rows with NaN values in the 'Handicap' column
    hc_long = hc_long.dropna(subset=['Handicap'])

    logger.info(f"Handicap data loaded: {len(hc_long)} player-TEG combinations")
    return hc_long