import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Import both navigation systems
from utils import (
    add_navigation_links,
    add_custom_navigation_links,
    apply_custom_navigation_css,
    create_custom_navigation_section,
    PAGE_DEFINITIONS,
    get_app_base_url
)

st.set_page_config(
    page_title="Navigation Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Navigation System Test Page")

st.markdown("""
This page demonstrates the different navigation approaches available in the TEG app.
You can compare the standard `st.page_link()` approach with the new custom HTML navigation system.
""")

# Show current environment info
st.subheader("Environment Information")
col1, col2 = st.columns(2)
with col1:
    st.metric("Base URL", get_app_base_url())
with col2:
    st.metric("Test Page", "navigation_test.py")

st.markdown("---")

# Split into two columns for comparison
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔗 Standard Navigation (st.page_link)")
    st.markdown("*Current system using Streamlit's built-in page_link function*")

    # Add standard navigation for Records section (since this page isn't in PAGE_DEFINITIONS)
    # We'll manually create it for demonstration
    st.markdown("**Links to Records pages:**")
    records_pages = [
        "300TEG Records.py",
        "301Best_TEGs_and_Rounds.py",
        "302Personal Best Rounds & TEGs.py"
    ]

    cols = st.columns(len(records_pages))
    for i, page_file in enumerate(records_pages):
        page_info = PAGE_DEFINITIONS.get(page_file, {})
        title = page_info.get("title", page_file)
        with cols[i]:
            st.page_link(page_file, label=title)

with col2:
    st.subheader("✨ Custom HTML Navigation")
    st.markdown("*New system with full CSS control*")

    # Apply custom CSS
    apply_custom_navigation_css("default")

    st.markdown("**Links to Records pages:**")

    # Create custom navigation manually
    import os
    base_url = get_app_base_url()
    nav_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">'

    for page_file in records_pages:
        page_info = PAGE_DEFINITIONS.get(page_file, {})
        title = page_info.get("title", page_file)
        page_name = page_file.replace('.py', '').replace(' ', '_')
        full_url = f"{base_url}/{page_name}"

        nav_html += f'''
        <a href="{full_url}"
           target="_self"
           class="custom-nav-link"
           style="flex: 1; min-width: 200px; text-align: center;">
           {title}
        </a>
        '''

    nav_html += '</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

st.markdown("---")

# CSS Theme Showcase
st.subheader("🎨 CSS Theme Showcase")
st.markdown("Different styling themes available for custom navigation:")

# Create tabs for different themes
theme_tabs = st.tabs(["Default", "Modern", "Minimal", "Glass", "Neon", "Material"])

themes = ["default", "modern", "minimal", "glass", "neon", "material"]
sample_pages = ["300TEG Records.py", "301Best_TEGs_and_Rounds.py"]

for i, (tab, theme) in enumerate(zip(theme_tabs, themes)):
    with tab:
        st.markdown(f"**{theme.title()} Theme**")

        # Apply theme-specific CSS
        if theme == "neon":
            st.markdown("""
            <style>
            .custom-nav-link.theme-neon {
                background: transparent;
                color: #00ffff !important;
                border: 1px solid #00ffff;
                text-shadow: 0 0 5px #00ffff;
                box-shadow: 0 0 5px rgba(0, 255, 255, 0.3);
                padding: 0.75rem 1.25rem;
                margin: 0.25rem;
                text-decoration: none !important;
                border-radius: 6px;
                transition: all 0.3s ease;
                display: inline-block;
            }
            .custom-nav-link.theme-neon:hover {
                background: rgba(0, 255, 255, 0.1);
                box-shadow: 0 0 15px rgba(0, 255, 255, 0.6), 0 0 30px rgba(0, 255, 255, 0.3);
                text-shadow: 0 0 10px #00ffff;
                text-decoration: none !important;
            }
            </style>
            """, unsafe_allow_html=True)
        elif theme == "material":
            st.markdown("""
            <style>
            .custom-nav-link.theme-material {
                background: #f5f5f5;
                color: #333 !important;
                border: none;
                border-radius: 4px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                padding: 0.75rem 1.25rem;
                margin: 0.25rem;
                text-decoration: none !important;
                transition: all 0.3s ease;
                display: inline-block;
            }
            .custom-nav-link.theme-material:hover {
                background: #e0e0e0;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
                text-decoration: none !important;
            }
            </style>
            """, unsafe_allow_html=True)

        # Create sample navigation with theme
        nav_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0;">'

        for page_file in sample_pages:
            page_info = PAGE_DEFINITIONS.get(page_file, {})
            title = page_info.get("title", page_file)
            page_name = page_file.replace('.py', '').replace(' ', '_')
            full_url = f"{base_url}/{page_name}"

            nav_html += f'''
            <a href="{full_url}"
               target="_self"
               class="custom-nav-link theme-{theme}"
               style="flex: 1; min-width: 200px; text-align: center;">
               {title}
            </a>
            '''

        nav_html += '</div>'
        st.markdown(nav_html, unsafe_allow_html=True)

        if theme == "minimal":
            st.info("💡 The minimal theme works best for inline text navigation")
        elif theme == "glass":
            st.info("💡 The glass theme requires a background for the blur effect to be visible")
        elif theme == "neon":
            st.info("💡 The neon theme works best on dark backgrounds")

st.markdown("---")

# Usage Examples
st.subheader("📚 Usage Examples")

st.markdown("### 1. Simple Custom Navigation")
st.code("""
# Import functions
from utils import add_custom_navigation_links, apply_custom_navigation_css

# Apply CSS theme
apply_custom_navigation_css("modern")

# Add navigation (same as current system, but with custom HTML)
add_custom_navigation_links(__file__)
""", language="python")

st.markdown("### 2. Advanced Custom Navigation")
st.code("""
# Import functions
from utils import create_custom_navigation_section, PAGE_DEFINITIONS, get_app_base_url

# Create fully custom navigation with specific styling
section_pages = ["300TEG Records.py", "301Best_TEGs_and_Rounds.py"]
nav_html = create_custom_navigation_section("Records", section_pages, "current_page.py")

# Apply custom CSS and display
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown(nav_html, unsafe_allow_html=True)
""", language="python")

st.markdown("### 3. Load External CSS")
st.code("""
# Load styles from the CSS file
with open("styles/navigation.css", "r") as f:
    css_content = f.read()

st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
""", language="python")

st.markdown("---")

# Test all functions
st.subheader("🔧 Function Tests")

with st.expander("Test get_app_base_url()"):
    st.code(f"get_app_base_url() = '{get_app_base_url()}'")

with st.expander("Test URL generation"):
    test_files = ["300TEG Records.py", "101TEG History.py", "leaderboard.py"]
    for test_file in test_files:
        page_name = test_file.replace('.py', '').replace(' ', '_')
        full_url = f"{get_app_base_url()}/{page_name}"
        st.code(f"{test_file} → {full_url}")

with st.expander("Show PAGE_DEFINITIONS"):
    st.json(PAGE_DEFINITIONS)

# Footer
st.markdown("---")
st.markdown("""
**Note:** This test page demonstrates the custom navigation system.
The navigation links will work in both local development and Railway deployment
thanks to the dynamic URL detection system.

**Next Steps:**
1. Choose your preferred theme
2. Replace `add_navigation_links(__file__)` with `add_custom_navigation_links(__file__)`
3. Add theme CSS with `apply_custom_navigation_css("theme_name")`
""")

st.markdown("### 🚀 Quick Implementation")
st.info("""
To implement custom navigation on any page:

1. **Replace** `add_navigation_links(__file__)`
2. **With** `add_custom_navigation_links(__file__)`
3. **Add** `apply_custom_navigation_css("modern")` before the navigation call
""")