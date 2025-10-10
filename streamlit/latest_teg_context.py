"""Streamlit page for analyzing a selected TEG in context.

This page allows users to select a TEG and view its performance in comparison
to all other TEGs. It provides a comprehensive analysis through a tabbed
interface, including:
- **Aggregate Score**: Compares the selected TEG against others on various
  metrics (Score, Stableford, Gross vs. Par, Net vs. Par).
- **Scoring**: Shows the distribution of scores (Gross vs. Par or Stableford)
  for the selected TEG.
- **Streaks**: Displays the longest streaks for various achievements within
  the selected TEG.
- **Records & PBs**: Highlights any all-time records or personal bests
  achieved in the selected TEG.

The page uses helper functions to:
- Load and process ranked TEG data.
- Create interactive charts and tables for comparison.
- Identify and display records and personal bests.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import importlib.util

# Import data loading functions from main utils
from utils import get_ranked_teg_data, load_datawrapper_css, load_all_data, read_file, STREAKS_PARQUET, read_text_file, load_teg_reports_css

# Import latest round/TEG helper functions (shared helper file)
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    initialize_teg_selection_state,
    update_teg_session_state_defaults,
    create_teg_selection_reset_function,
    get_teg_options,
    create_metric_tabs_data,
    prepare_teg_context_display
)

# Import score count processing
from helpers.score_count_processing import count_scores_by_player

# Import streak analysis functions
from helpers.streak_analysis_processing import get_player_window_streaks


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
        st.error("Markdown library not available. Please install with: pip install markdown")


# === CONFIGURATION ===
# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
st.subheader("TEG context")
st.markdown('Shows how latest or selected TEG compares to other TEGs')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Load TEG reports CSS styling for the report tab
load_teg_reports_css()

# initialize_teg_selection_state() - Sets up session state for TEG selection
initialize_teg_selection_state()


# === DATA LOADING ===
# Load ranked TEG data for context analysis
# Purpose: Provides ranking context to show how selected TEG compares to all other TEGs
df_teg = get_ranked_teg_data().sort_values(by='TEGNum')

# Load all data including incomplete TEGs for scoring and streaks analysis
# Purpose: TEG analysis benefits from current tournament data for up-to-date context
all_data = load_all_data(exclude_incomplete_tegs=False)

# update_teg_session_state_defaults() - Sets session state to latest TEG if not initialized
update_teg_session_state_defaults(df_teg)

# create_teg_selection_reset_function() - Creates callback for "Latest TEG" button
reset_teg_selection = create_teg_selection_reset_function(df_teg)


# === USER INTERFACE ===
# TEG selection controls
col1, col2 = st.columns(2)

with col1:
    # get_teg_options() - Gets available TEG options
    teg_options = get_teg_options(df_teg)
    teg_index = teg_options.index(st.session_state.teg_t)
    teg_t = st.selectbox("Select TEG", options=teg_options, index=teg_index, key='teg_t_select')
    st.session_state.teg_t = teg_t

with col2:
    st.button("Latest TEG", on_click=reset_teg_selection)

# === MAIN TAB STRUCTURE ===
main_tabs = st.tabs(["Aggregate Score", "Scoring", "Streaks", "Records & PBs", "Report"])

# === AGGREGATE SCORE TAB ===
with main_tabs[0]:
    # Metric tabs setup
    metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']

    # create_metric_tabs_data() - Prepares metric names and friendly labels for tabs
    metrics, friendly_metrics = create_metric_tabs_data(metrics)
    metric_tabs = st.tabs(friendly_metrics)

    # get_round_metric_mappings() - Gets mapping for metric name conversion
    name_mapping, inverted_name_mapping = get_round_metric_mappings()

    # Display metric-specific analysis in each tab
    for tab, friendly_metric in zip(metric_tabs, friendly_metrics):
        with tab:
            st.markdown(f"#### {friendly_metric}")

            # Convert friendly name back to internal metric name
            metric = name_mapping.get(friendly_metric, friendly_metric)

            # prepare_teg_context_display() - Creates context table for selected TEG
            context_display = prepare_teg_context_display(df_teg, teg_t, metric, friendly_metric)
            st.write(
                context_display.to_html(
                    index=False,
                    justify='left',
                    classes='jb-table-test, datawrapper-table full-width'
                ),
                unsafe_allow_html=True
            )

# === SCORING TAB ===
with main_tabs[1]:
    st.markdown("#### Scoring")

    # Scoring type toggle
    scoring_type = st.segmented_control(
        "Scoring type",
        options=["Gross vs Par", "Stableford"],
        default="Gross vs Par"
    )

    # Extract TEGNum from TEG string (e.g., "TEG 17" -> 17)
    teg_num = int(teg_t.split()[1])

    # Filter data for selected TEG (all rounds)
    teg_data = all_data[all_data['TEGNum'] == teg_num]

    # Count scores across all rounds in the TEG
    if scoring_type == "Gross vs Par":
        score_counts = count_scores_by_player(teg_data, field='GrossVP')
        score_counts = score_counts.reset_index()
        score_counts.columns.name = None

        # Format vs par values
        from utils import format_vs_par
        score_counts['GrossVP'] = score_counts['GrossVP'].apply(format_vs_par)
        score_counts = score_counts.rename(columns={'GrossVP': 'vs Par'})

        # Replace 0 values with '-' in player columns
        player_cols = [col for col in score_counts.columns if col != 'vs Par']
        for col in player_cols:
            score_counts[col] = score_counts[col].replace(0, '-')
    else:
        score_counts = count_scores_by_player(teg_data, field='Stableford')
        # Sort by Stableford value in descending order
        score_counts = score_counts.sort_index(ascending=False)
        score_counts = score_counts.reset_index()
        score_counts.columns.name = None

        # Convert Stableford column to integer
        score_counts['Stableford'] = score_counts['Stableford'].astype(int)

        # Replace 0 values with '-' in player columns
        player_cols = [col for col in score_counts.columns if col != 'Stableford']
        for col in player_cols:
            score_counts[col] = score_counts[col].replace(0, '-')

        score_counts = score_counts.rename(columns={'Stableford': 'Stableford'})

    # Display score count table
    st.write(
        score_counts.to_html(
            index=False,
            justify='left',
            classes='datawrapper-table'
        ),
        unsafe_allow_html=True
    )

# === STREAKS TAB ===
with main_tabs[2]:
    st.markdown("#### Streaks")

    # Load streak data
    streaks_df = read_file(STREAKS_PARQUET)

    # Get streaks for the selected TEG (all rounds)
    # Extract TEGNum from TEG string (e.g., "TEG 17" -> 17)
    teg_num = int(teg_t.split()[1])

    # For TEG-level streaks, we need to get streaks across all rounds in the TEG
    # We'll get the last round of the TEG and show cumulative streaks through that round
    teg_rounds = all_data[all_data['TEGNum'] == teg_num]['Round'].unique()
    if len(teg_rounds) > 0:
        last_round = max(teg_rounds)

        teg_streaks = get_player_window_streaks(
            all_data,
            streaks_df,
            teg=teg_t,
            round_num=last_round
        )

        if len(teg_streaks) > 0:
            # Pivot table to show players in columns and streak types in rows
            streaks_pivot = teg_streaks.pivot(
                index='Streak Type',
                columns='Player',
                values='Max Streak'
            )

            # Reset index to make Streak Type a column
            streaks_pivot = streaks_pivot.reset_index()

            # Remove the columns name to avoid extra header
            streaks_pivot.columns.name = None

            # Define streak mapping for filtering and renaming
            streak_mapping = {
                'Eagles': 'Eagles',
                'Birdies': 'Birdies',
                'Pars or Better': 'Pars',
                'No +2s': 'Bogeys',
                'Over Par': 'Over par',
                'TBPs': 'TBPs'
            }

            # Filter to only show desired streaks and apply mapping
            streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'].isin(streak_mapping.keys())].copy()
            streaks_pivot['Streak Type'] = streaks_pivot['Streak Type'].map(streak_mapping)

            # Define desired order
            desired_order = ['Eagles', 'Birdies', 'Pars', 'Bogeys', 'Over par', 'TBPs']

            # Sort by desired order
            streaks_pivot['_order'] = streaks_pivot['Streak Type'].map({s: i for i, s in enumerate(desired_order)})
            streaks_pivot = streaks_pivot.sort_values('_order').drop('_order', axis=1)

            # Filter out Eagles and Birdies rows if all values are 0
            # Get player columns (all except 'Streak Type')
            player_cols = [col for col in streaks_pivot.columns if col != 'Streak Type']

            # Remove Eagles row only if ALL players have 0 (max value is 0)
            if 'Eagles' in streaks_pivot['Streak Type'].values:
                eagles_max = streaks_pivot[streaks_pivot['Streak Type'] == 'Eagles'][player_cols].max(axis=1).iloc[0]
                if eagles_max == 0:
                    streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'] != 'Eagles']

            # Remove Birdies row only if ALL players have 0 (max value is 0)
            if 'Birdies' in streaks_pivot['Streak Type'].values:
                birdies_max = streaks_pivot[streaks_pivot['Streak Type'] == 'Birdies'][player_cols].max(axis=1).iloc[0]
                if birdies_max == 0:
                    streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'] != 'Birdies']

            # Display pivoted streaks table
            st.write(
                streaks_pivot.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )

            st.caption("Eagles / birdies / par / bogeys are all 'or better'")
        else:
            st.info("No streak data available for this TEG.")
    else:
        st.info("No data available for this TEG.")

# === RECORDS & PBs TAB ===
with main_tabs[3]:
    st.markdown("#### Records & Personal Bests")

    from helpers.records_identification import (
        identify_aggregate_records_and_pbs,
        identify_all_time_worsts,
        identify_streak_records,
        identify_score_count_records,
        display_records_and_pbs_summary
    )

    # Collect all records and PBs
    records_dict = {}

    # Phase 1: Aggregate score records and PBs
    aggregate_results = identify_aggregate_records_and_pbs(df_teg, teg_t)
    records_dict.update({
        'aggregate_records': aggregate_results['records'],
        'aggregate_pbs': aggregate_results['personal_bests'],
        'aggregate_worsts': aggregate_results['personal_worsts']
    })

    # All-time worsts
    all_time_worsts = identify_all_time_worsts(df_teg, teg_t)
    records_dict.update({
        'all_time_worsts': all_time_worsts
    })

    # Phase 3: Streak records
    streak_results = identify_streak_records(all_data, streaks_df, teg_t)
    records_dict.update({
        'streak_records': streak_results['records']
    })

    # Score count records
    score_count_results = identify_score_count_records(all_data, teg_t)
    records_dict.update({
        'best_score_counts': score_count_results['best_score_counts'],
        'worst_score_counts': score_count_results['worst_score_counts']
    })

    # Display records and PBs summary
    display_records_and_pbs_summary(records_dict, page_type='TEG')

# === REPORT TAB ===
with main_tabs[4]:
    st.markdown("#### Tournament Report")

    # Extract TEG number from teg_t string (e.g., "TEG 17" -> 17)
    try:
        teg_num = int(teg_t.split()[-1])
    except (ValueError, IndexError):
        st.error(f"Could not extract TEG number from '{teg_t}'")
        teg_num = None

    if teg_num is not None:
        # Determine if tournament is complete
        try:
            completed_tegs = read_file('data/completed_tegs.csv')
            is_complete = not completed_tegs.empty and teg_num in completed_tegs['TEGNum'].values
        except Exception:
            # Fallback: assume complete if we have the data
            is_complete = True

        if is_complete:
            # Construct path to report file (relative path from project root)
            report_file_path = f"data/commentary/teg_{teg_num}_main_report.md"

            # Try to load and render the report
            try:
                md_text = read_text_file(report_file_path)
                if teg_num < 8:
                    st.caption("NB: The TEG Trophy winners before TEG 8 were decided by best net; the report here is written based on Stableford so finishing positions may be inaccurate")
                render_report(md_text)
            except FileNotFoundError:
                st.info(f"No report available yet for {teg_t}.")
            except Exception as report_error:
                st.error(f"Error loading report: {str(report_error)}")
        else:
            st.info(f"No report available - tournament in progress.")

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
