"""
CSS styles specific to the Records pages.
Separated into its own file for better organization and reusability.
"""

import streamlit as st


def load_records_page_css():
    """
    Load CSS styles for TEG Records pages.
    
    Purpose:
        - Formats stat sections with consistent background and spacing
        - Styles record display cards with proper typography
        - Creates visual separation between different record types
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
            background-color: rgb(240, 242, 246);
            padding: 20px;
            margin: 5px;
        }
        
        .stat-section h2 {
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
        }
        
        .stat-details {
            font-size: 16px;
            color: #999;
            line-height: 1.4;
        }
        
        .stat-details .Player {
            color: #666;
        }
        
        </style>
        """, unsafe_allow_html=True)