"""Main navigation configuration for the Streamlit application.

This script sets up the primary navigation for the TEG Streamlit application
using `st.navigation`. It dynamically generates the navigation structure based
on the page definitions in `page_config.py` and the current status of the TEG
tournaments (i.e., whether there is an incomplete TEG).

The script also injects custom CSS to style the sidebar and top navigation bar,
ensuring a consistent look and feel across the application.
"""
import os
import streamlit as st
from pathlib import Path
from streamlit_extras.stylable_container import stylable_container
import sys
sys.path.append(str(Path(__file__).parent))
from utils import has_incomplete_teg_fast
from page_config import generate_navigation_structure


st.markdown(
    """
    <style>
    /* Keep for sidebar layout */
    [data-testid="stSidebar"]::before {
        content: "The El Golfo";
        display: block;
        font-size: 1.8rem;
        font-weight: bold;
        padding: 0.6rem 1rem 0.2rem 1rem;
        color: var(--text-color);
        font-family: var(--font);
    }

    /* TOP NAV: layout + spacing */
    [data-testid="stToolbar"] {
        display: flex;              /* ensure single row */
        align-items: center;
        flex-wrap: nowrap;          /* prevent wrapping */
        padding-left: 0.75rem;      /* small left padding */
        gap: 1rem;                  /* space between title and nav */
    }

    /* TOP NAV: title */
    [data-testid="stToolbar"]::before {
        content: "The El Golfo";
        font-size: 1.6rem;
        font-weight: bold;
        line-height: 1;
        white-space: nowrap;        /* keep on one line */
        color: var(--text-color);
        font-family: var(--font);
    }

    /* Hide titles on small screens */
    @media (max-width: 640px) {
        [data-testid="stSidebar"]::before,
        [data-testid="stToolbar"]::before {
            display: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)



# Check if there are incomplete TEGs to determine navigation structure
try:
    has_incomplete_teg = has_incomplete_teg_fast()
except:
    # If there's any error checking for incomplete TEGs, default to no incomplete TEG
    has_incomplete_teg = False

# Generate navigation structure from page configuration
nav_structure = generate_navigation_structure(has_incomplete_teg)

pg = st.navigation(nav_structure, position='top')

pg.run()