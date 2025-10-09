"""CSS styles specific to the Records pages.

This module contains a function to load the CSS styles used on the TEG
Records pages for better organization and reusability.
"""

import streamlit as st


def load_records_page_css():
    """Loads the CSS styles for the TEG Records pages.

    This function injects custom CSS into the Streamlit app to format the stat
    sections, style the record display cards, and create visual separation
    between different record types.
    """
    st.markdown("""
        <style>
        
        div[data-testid="column"] {
            background-color: #f0f0f0;
            border-radius: 10px;
            padding: 20px;
            height: 100%;
        }
        
        .stat-section {
            margin-bottom: 20px;
            /* background-color: rgb(240, 242, 246); */
            background-color: #F3F7F3;
            padding: 20px;
            margin: 5px;
        }
        
        .stat-section h2 {
            # font-family: 'Roboto Mono', monospace;
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
            # font-family: monospace;
        }
        
        .stat-details {
            font-family: 'Roboto Mono', monospace;;
            font-size: 16px;
            color: #999;
            # color: #666;
            line-height: 1.4;
        }
        
        .stat-details .Player {
            # color: #666;
        }
        
        </style>
        """, unsafe_allow_html=True)