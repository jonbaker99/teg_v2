import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Import navigation functions
from utils import (
    create_custom_page_link,
    PAGE_DEFINITIONS
)

st.set_page_config(
    page_title="Navigation Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Navigation System Test Page")

st.markdown("""
This page compares the two navigation approaches available in the TEG app.
""")

# Test pages for both sections
test_pages = [
    "300TEG Records.py",  # numbered
    "101TEG History.py",  # numbered
    "leaderboard.py",     # non-numbered
    "streaks.py"          # non-numbered
]

# ===== CUSTOM HTML NAVIGATION (TOP) =====
st.subheader("✨ Custom HTML Navigation")
st.markdown("*New system with full CSS control*")

st.markdown("**Links to test pages:**")

# Create custom navigation using individual links
cols = st.columns(len(test_pages))
for i, page_file in enumerate(test_pages):
    create_custom_page_link(page_file, cols[i], css_class="custom-nav-link")

st.markdown("---")

# ===== STANDARD NAVIGATION (BOTTOM) =====
st.subheader("🔗 Standard Navigation (st.page_link)")
st.markdown("*Current system using Streamlit's built-in page_link function*")

st.markdown("**Links to test pages:**")

cols = st.columns(len(test_pages))
for i, page_file in enumerate(test_pages):
    page_info = PAGE_DEFINITIONS.get(page_file, {})
    title = page_info.get("title", page_file)
    with cols[i]:
        st.page_link(page_file, label=title)