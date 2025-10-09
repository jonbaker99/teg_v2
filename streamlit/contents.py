"""Contents page - Site map showing all sections and pages."""
import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from page_config import PAGE_DEFINITIONS, SECTION_CONFIG
from utils import (
    apply_custom_navigation_css,
    get_app_base_url,
    convert_filename_to_streamlit_url,
    get_page_layout
)

# === PAGE LAYOUT CONFIGURATION ===
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)

st.title("TEG Contents")

st.markdown("A complete list of all pages in The El Golfo site.")

# Apply navigation CSS for consistent link styling
apply_custom_navigation_css()

# Group pages by section
sections = {}
for filename, page_info in PAGE_DEFINITIONS.items():
    section = page_info["section"]
    if section not in sections:
        sections[section] = []
    sections[section].append((filename, page_info))

# Get sections in order (excluding Data and Contents sections)
section_order = []
for section in sections.keys():
    if section in ["Data", "Contents"]:  # Exclude data management and contents sections
        continue
    section_config = SECTION_CONFIG.get(section, {})
    order = section_config.get("order", 999)
    display_name = section_config.get("display_name", section)
    section_order.append((order, section, display_name))

section_order.sort(key=lambda x: x[0])

# Display sections in rows of 3 columns
base_url = get_app_base_url()
num_cols = 3

for row_start in range(0, len(section_order), num_cols):
    row_sections = section_order[row_start:row_start + num_cols]
    # Always create num_cols columns to maintain consistent width
    cols = st.columns(num_cols, vertical_alignment="top", gap="medium")

    for col_idx, (order, section, display_name) in enumerate(row_sections):
        with cols[col_idx]:
            st.markdown(f"#### {display_name}")

            # Build links for all pages in this section
            links_html = []

            for filename, page_info in sections[section]:
                title = page_info.get("title", filename)
                icon = page_info.get("icon", "")
                page_name = convert_filename_to_streamlit_url(filename)
                full_url = f"{base_url}/{page_name}"

                # Create link with icon
                label = f"{icon} {title}".strip() if icon else title
                link_html = f'<a href="{full_url}" target="_self" class="custom-nav-link">{label}</a>'
                links_html.append(link_html)

            # Display links as vertical list
            st.markdown("<br/>".join(links_html), unsafe_allow_html=True)
