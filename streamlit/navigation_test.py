import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Import navigation functions
from utils import (
    add_custom_navigation_links,
    PAGE_DEFINITIONS
)

st.set_page_config(
    page_title="Navigation Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Navigation Layout Options")

st.markdown("""
This page demonstrates the different layout options for navigation links.
Using the "History" section as an example to test main page URL handling.
""")

# ===== HORIZONTAL LAYOUTS =====
st.subheader("📍 Horizontal Layouts")

st.markdown("**Horizontal with pipe separator:**")
add_custom_navigation_links("101TEG Honours Board.py", layout="horizontal", separator=" | ")

st.markdown("**Horizontal with dash separator:**")
add_custom_navigation_links("101TEG Honours Board.py", layout="horizontal", separator=" - ")

st.markdown("**Horizontal with spaces:**")
add_custom_navigation_links("101TEG Honours Board.py", layout="horizontal", separator="   ")

st.markdown("**Horizontal with bullet separator:**")
add_custom_navigation_links("101TEG Honours Board.py", layout="horizontal", separator=" • ")

st.markdown("---")

# ===== VERTICAL LAYOUT =====
st.subheader("📝 Vertical Layout")

st.markdown("**Vertical (each link on new line):**")
add_custom_navigation_links("101TEG Honours Board.py", layout="vertical")

st.markdown("---")

# ===== COLUMN LAYOUT (ORIGINAL) =====
st.subheader("📋 Column Layout (Original)")

st.markdown("**Columns (original layout):**")
add_custom_navigation_links("101TEG Honours Board.py", layout="columns")