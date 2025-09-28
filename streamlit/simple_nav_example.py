import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from utils import add_simple_navigation_links, add_navigation_links

st.set_page_config(
    page_title="Simple Navigation Example",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Simple Navigation Styling Example")

st.markdown("""
This page shows the **simplest way** to get custom styling control over navigation links.
Just font, color, size, and hover color - nothing more.
""")

# Show the current (standard) navigation first
st.subheader("Current Navigation (st.page_link)")
add_navigation_links(__file__)

st.markdown("---")

# Show simple custom navigation
st.subheader("Simple Custom Navigation")

st.markdown("**Default simple styling:**")
add_simple_navigation_links(__file__)

st.markdown("---")

st.subheader("Custom Font & Colors")

# Example with custom styling
st.markdown("**Custom font and colors:**")
add_simple_navigation_links(
    __file__,
    font_family="Georgia, serif",
    font_size="18px",
    color="#d32f2f",
    hover_color="#8b0000"
)

st.markdown("---")

st.subheader("Different Sizes")

st.markdown("**Large links:**")
add_simple_navigation_links(
    __file__,
    font_size="1.2rem",
    color="#2e7d32",
    hover_color="#1b5e20"
)

st.markdown("**Small links:**")
add_simple_navigation_links(
    __file__,
    font_size="0.9rem",
    color="#7b1fa2",
    hover_color="#4a148c"
)

st.markdown("---")

st.subheader("Implementation")

st.markdown("**All you need is one line:**")
st.code('''
from utils import add_simple_navigation_links

# Replace this:
add_navigation_links(__file__)

# With this:
add_simple_navigation_links(__file__)
''', language="python")

st.markdown("**For custom styling:**")
st.code('''
add_simple_navigation_links(
    __file__,
    font_family="Arial, sans-serif",  # Any CSS font family
    font_size="16px",                 # Any CSS size unit
    color="#1e90ff",                  # Any CSS color
    hover_color="#0066cc"             # Any CSS color
)
''', language="python")

st.markdown("---")

st.info("""
💡 **This is the recommended approach** if you just want basic font/color control.

The complex CSS system with themes is still available if you need advanced effects later.
""")