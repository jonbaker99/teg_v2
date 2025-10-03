"""Streamlit page for testing and demonstrating navigation components.

This page serves as a test harness for the `add_custom_navigation_links`
function, showcasing its different layout options and input methods. It is
intended for development and debugging purposes to ensure that the navigation
components behave as expected.
"""
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

"---"

import streamlit as st

st.title("add_custom_navigation_links – test harness")

st.write("This page exercises all layouts with `render=True` and `render=False` using `input_value='History'`.")

# --- 1) HORIZONTAL -----------------------------------------------------------
st.subheader("Horizontal")
st.caption("render=True (backward-compatible)")
st.markdown("**Related links:**")
add_custom_navigation_links("History", layout="horizontal", separator=" | ", render=True)

st.caption("render=False (inline the label + links in one call to remove spacing)")
links_html = add_custom_navigation_links("History", layout="horizontal", separator=" | ", render=False)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)

st.divider()

# --- 2) VERTICAL --------------------------------------------------------------
st.subheader("Vertical")
st.caption("render=True (backward-compatible)")
st.markdown("**Related links:**")
add_custom_navigation_links("History", layout="vertical", render=True)

st.caption("render=False (compose yourself; here we add a line break after the label)")
links_html_v = add_custom_navigation_links("History", layout="vertical", render=False)
st.markdown(f"**Related links:**<br/>{links_html_v}", unsafe_allow_html=True)

st.divider()

# --- 3) COLUMNS ---------------------------------------------------------------
st.subheader("Columns")
st.caption("render=True (backward-compatible)")
st.markdown("**Related links:**")
add_custom_navigation_links("History", layout="columns", render=True)

st.caption("render=False (returns List[List[str]]; you decide placement)")
cols_links = add_custom_navigation_links("History", layout="columns", render=False)
num_cols = len(cols_links)
st.markdown("**Related links:**")
cols = st.columns(num_cols)

for i, links_in_col in enumerate(cols_links):
    with cols[i]:
        # Join links in each column with a separator if there are multiple
        if links_in_col:
            st.markdown(" | ".join(links_in_col), unsafe_allow_html=True)
        else:
            st.write("")  # keep column alignment even if empty
