import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Import navigation functions
from utils import (
    add_custom_navigation_links,
    PAGE_DEFINITIONS,
    SECTION_LAYOUTS
)

st.set_page_config(
    page_title="Navigation Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Navigation Layout Options")

st.markdown("""
This page demonstrates the different layout options and input methods for navigation links.
""")

# ===== SECTION-BASED NAVIGATION =====
st.subheader("🎯 Section-Based Navigation (New Feature)")

for section in SECTION_LAYOUTS.keys():
    st.markdown(section)
    add_custom_navigation_links(section, layout="horizontal", separator=" | ")


st.markdown("**All History pages (using section name):**")
add_custom_navigation_links("History", layout="horizontal", separator=" | ")
# add_custom_navigation_links("Records", layout="horizontal", separator=" | ")


st.markdown("**All Records pages (using section name):**")
add_custom_navigation_links("Records", layout="horizontal", separator=" - ")

st.markdown("---")

# ===== PAGE-BASED NAVIGATION =====
st.subheader("📄 Page-Based Navigation (Original)")

st.markdown("**Other History pages (excluding current page):**")
add_custom_navigation_links("101TEG Honours Board.py", layout="horizontal", separator=" | ")

st.markdown("**Other Records pages (excluding current page):**")
add_custom_navigation_links("300TEG Records.py", layout="horizontal", separator=" | ")

st.markdown("---")

# ===== LAYOUT DEMONSTRATIONS =====
st.subheader("📍 Layout Options")

st.markdown("**Horizontal with different separators:**")
add_custom_navigation_links("History", layout="horizontal", separator=" • ")

st.markdown("**Vertical layout:**")
add_custom_navigation_links("Records", layout="vertical")

st.markdown("**Column layout:**")
add_custom_navigation_links("History", layout="columns")