"""TEG Reports page for viewing round and tournament reports.

This page displays round-by-round reports and full TEG tournament reports
for any selected TEG (defaulting to the latest). It provides:
- A dropdown to select any TEG (sorted by TEGNum)
- Tabbed interface with round reports for each completed round
- Full TEG report tab (for completed TEGs only)
"""
# === IMPORTS ===
import streamlit as st
import importlib.util
from utils import (
    read_text_file,
    read_file,
    load_all_data,
    get_teg_rounds,
    load_datawrapper_css,
    load_teg_reports_css
)

# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)

# === CONFIGURATION ===
st.subheader("TEG Reports")
st.markdown("Round reports and tournament summaries")

# Load CSS styling
load_datawrapper_css()
load_teg_reports_css()

# === HELPER FUNCTIONS ===
def render_report(md_text: str):
    """Render markdown report as HTML with TEG report styling

    Args:
        md_text (str): Markdown text to render
    """
    has_markdown = importlib.util.find_spec("markdown") is not None
    if has_markdown:
        import markdown as md
        html_body = md.markdown(md_text, extensions=["extra", "sane_lists", "smarty", "toc"])
        full_html = f"<div class='teg-report'>{html_body}</div>"
        st.markdown(full_html, unsafe_allow_html=True)
    else:
        # Fallback to standard markdown rendering if library not available
        st.markdown(md_text)


# === DATA LOADING ===
try:
    # Load complete dataset to get all TEGs
    all_data = load_all_data(exclude_teg_50=True)

    # Get list of all TEGs sorted by TEGNum
    teg_order = all_data[['TEG', 'TEGNum']].drop_duplicates().sort_values('TEGNum')
    teg_options = teg_order['TEG'].tolist()

    if not teg_options:
        st.warning("No TEGs available in the data.")
        st.stop()

    # Get the latest TEG as default
    default_teg = all_data.loc[all_data['TEGNum'].idxmax(), 'TEG']
    default_index = teg_options.index(default_teg)

except Exception as e:
    st.error(f"Error loading TEG data: {str(e)}")
    st.stop()

# === TEG SELECTOR ===
chosen_teg = st.selectbox(
    "Select TEG",
    options=teg_options,
    index=default_index,
    key='teg_selector'
)

# Extract TEG number
selected_teg_num = int(chosen_teg.split()[-1])

# === GET SELECTED TEG INFO ===
try:
    # Determine if tournament is complete or in progress
    try:
        completed_tegs = read_file('data/completed_tegs.csv')
        if not completed_tegs.empty and selected_teg_num in completed_tegs['TEGNum'].values:
            num_rounds = completed_tegs[completed_tegs['TEGNum'] == selected_teg_num]['Rounds'].iloc[0]
            is_complete = True
        else:
            # Check if TEG is in progress
            in_progress_tegs = read_file('data/in_progress_tegs.csv')
            if not in_progress_tegs.empty and selected_teg_num in in_progress_tegs['TEGNum'].values:
                num_rounds = in_progress_tegs[in_progress_tegs['TEGNum'] == selected_teg_num]['Rounds'].iloc[0]
                is_complete = False
            else:
                # Fallback to default method
                num_rounds = get_teg_rounds(chosen_teg)
                current_rounds = all_data[all_data['TEG'] == chosen_teg]['Round'].nunique()
                is_complete = current_rounds >= num_rounds
    except Exception:
        # Fallback to default method if status files not available
        num_rounds = get_teg_rounds(chosen_teg)
        current_rounds = all_data[all_data['TEG'] == chosen_teg]['Round'].nunique()
        is_complete = current_rounds >= num_rounds

except Exception as e:
    st.error(f"Error loading TEG information: {str(e)}")
    st.stop()

# === BUILD TAB STRUCTURE ===
# Create tabs for each round plus full TEG report (if complete)
tab_names = [f"Round {r}" for r in range(1, num_rounds + 1)]

if is_complete:
    # Move "Full TEG Report" to the start of the list
    tab_names = ["Full TEG Report"] + tab_names

round_tab_offset = 1 if is_complete else 0

# Create tabs
tabs = st.tabs(tab_names)

# === ROUND REPORT TABS ===
for i, round_num in enumerate(range(1, num_rounds + 1)):
    with tabs[i+round_tab_offset]:
        # st.markdown(f"#### TEG {selected_teg_num} - Round {round_num} Report")

        # Construct file path for round report (try both naming formats)
        report_path_new = f"data/commentary/round_reports/TEG{selected_teg_num}_R{round_num}_report.md"
        report_path_old = f"data/commentary/round_reports/teg_{selected_teg_num}_round_{round_num}_report.md"

        try:
            # Try new format first
            try:
                report_content = read_text_file(report_path_new)
            except FileNotFoundError:
                # Fall back to old format
                report_content = read_text_file(report_path_old)

            render_report(report_content)
        except FileNotFoundError:
            st.info(f"No round report available for TEG {selected_teg_num} Round {round_num}")
        except Exception as e:
            st.error(f"Error loading round report: {str(e)}")

# === FULL TEG REPORT TAB ===
if is_complete:
    with tabs[0]:
        # st.markdown(f"#### TEG {selected_teg_num} - Full Tournament Report")

        # Construct path to full TEG report file
        report_file_path = f"data/commentary/teg_{selected_teg_num}_main_report.md"

        try:
            # Load and render the report
            md_text = read_text_file(report_file_path)

            # Add caption for older TEGs with different competition format
            if selected_teg_num < 8:
                st.caption("NB: The TEG Trophy winners before TEG 8 were decided by best net; the report here is written based on Stableford so finishing positions may be inaccurate")

            render_report(md_text)
        except FileNotFoundError:
            st.info(f"No full tournament report available yet for TEG {selected_teg_num}.")
        except Exception as e:
            st.error(f"Error loading tournament report: {str(e)}")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
st.markdown("")
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
