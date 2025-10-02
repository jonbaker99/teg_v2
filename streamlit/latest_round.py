# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_round_data, load_all_data, load_datawrapper_css, read_file, STREAKS_PARQUET
from make_charts import create_round_graph

# Import latest round helper functions
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    initialize_round_selection_state,
    update_session_state_defaults,
    get_teg_and_round_options,
    create_metric_tabs_data,
    prepare_round_context_display
)

# Import scorecard generation functions
from scorecard_utils import (
    load_scorecard_css,
    generate_round_comparison_html,
    generate_round_comparison_html_mobile
)

# Import score count processing
from helpers.score_count_processing import count_scores_by_player

# Import streak analysis functions
from helpers.streak_analysis_processing import get_player_window_streaks


# === CONFIGURATION ===
st.subheader("Chosen Round in context")
st.markdown('Shows how latest or selected rounds and TEGs compare to other rounds')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Load scorecard CSS for scorecard tab
load_scorecard_css()

# initialize_round_selection_state() - Sets up session state for TEG/round selection
initialize_round_selection_state()


# === DATA LOADING ===
# Load ranked round data for context analysis
# Purpose: Provides ranking context to show how selected rounds compare to all other rounds
df_round = get_ranked_round_data()
df_round = df_round.sort_values(by=['TEGNum', 'Round'])

# Load all data including incomplete TEGs for cumulative charts
# Purpose: Round analysis benefits from current tournament data for up-to-date context
all_data = load_all_data(exclude_incomplete_tegs=False)

# update_session_state_defaults() - Sets session state to latest round if not initialized
update_session_state_defaults(df_round)


# === USER INTERFACE ===
# Round selection controls
col1, col2 = st.columns(2)

with col1:
    # get_teg_and_round_options() - Gets available TEG options
    teg_options, _ = get_teg_and_round_options(df_round, st.session_state.teg_r)
    teg_index = teg_options.index(st.session_state.teg_r)
    teg_r = st.selectbox("Select TEG (Round)", options=teg_options, index=teg_index, key='teg_r_select')
    st.session_state.teg_r = teg_r

with col2:
    # get_teg_and_round_options() - Gets available round options for selected TEG
    _, round_options = get_teg_and_round_options(df_round, teg_r)
    rd_index = round_options.index(st.session_state.rd_r) if st.session_state.rd_r in round_options else 0
    rd_r = st.selectbox("Select Round", options=round_options, index=rd_index, key='rd_r_select')
    st.session_state.rd_r = rd_r

# === MAIN TAB STRUCTURE ===
main_tabs = st.tabs(["Scoreboards", "Scorecard", "Scoring", "Streaks", "Records & PBs"])

# === SCOREBOARDS TAB ===
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

            # prepare_round_context_display() - Creates context table for selected round
            context_display = prepare_round_context_display(df_round, teg_r, rd_r, metric, friendly_metric)
            st.write(
                context_display.to_html(
                    index=False,
                    justify='left',
                    classes='jb-table-test, datawrapper-table'
                ),
                unsafe_allow_html=True
            )

            # create_round_graph() - Creates cumulative performance chart through selected round
            st.markdown(f"#### Cumulative {friendly_metric} through round")
            cum_metric = f'{metric} Cum Round'
            fig_rd = create_round_graph(
                all_data,
                chosen_teg=teg_r,
                chosen_round=rd_r,
                y_series=cum_metric,
                title=friendly_metric,
                y_axis_label=f'Cumulative {friendly_metric}'
            )
            st.plotly_chart(fig_rd, use_container_width=True, config=dict({'displayModeBar': False}))

# === SCORECARD TAB ===
with main_tabs[1]:
    st.markdown("#### Scorecard")

    # Scorecard view toggle
    scorecard_view = st.segmented_control(
        "Scorecard view",
        options=["Desktop", "Mobile"],
        default="Desktop"
    )

    # Extract TEGNum from TEG string (e.g., "TEG 17" -> 17)
    teg_num = int(teg_r.split()[1])

    # Generate appropriate scorecard
    if scorecard_view == "Desktop":
        scorecard_html = generate_round_comparison_html(teg_num, rd_r)
    else:
        scorecard_html = generate_round_comparison_html_mobile(teg_num, rd_r)

    st.markdown(scorecard_html, unsafe_allow_html=True)

# === SCORING TAB ===
with main_tabs[2]:
    st.markdown("#### Scoring")

    # Scoring type toggle
    scoring_type = st.segmented_control(
        "Scoring type",
        options=["Gross vs Par", "Stableford"],
        default="Gross vs Par"
    )

    # Extract TEGNum from TEG string (e.g., "TEG 17" -> 17)
    teg_num = int(teg_r.split()[1])

    # Filter data for selected round
    round_data = all_data[(all_data['TEGNum'] == teg_num) & (all_data['Round'] == rd_r)]

    # Count scores by player
    if scoring_type == "Gross vs Par":
        score_counts = count_scores_by_player(round_data, field='GrossVP')
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
        score_counts = count_scores_by_player(round_data, field='Stableford')
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
with main_tabs[3]:
    st.markdown("#### Streaks")

    # Load streak data
    streaks_df = read_file(STREAKS_PARQUET)

    # Get streaks for the selected round (teg_r is already in "TEG 17" format)
    round_streaks = get_player_window_streaks(
        all_data,
        streaks_df,
        teg=teg_r,
        round_num=rd_r
    )

    if len(round_streaks) > 0:
        # Pivot table to show players in columns and streak types in rows
        # Current format: ['Streak Type', 'Player', 'Max Streak', 'Location']
        # Target format: Streak Type | Player1 | Player2 | ...

        streaks_pivot = round_streaks.pivot(
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
        st.info("No streak data available for this round.")

# === RECORDS & PBs TAB ===
with main_tabs[4]:
    st.markdown("#### Records & Personal Bests")

    from helpers.records_identification import (
        identify_aggregate_records_and_pbs,
        identify_all_time_worsts,
        identify_9hole_records_and_pbs,
        identify_streak_records,
        identify_score_count_records,
        display_records_and_pbs_summary
    )

    # Collect all records and PBs
    records_dict = {}

    # Phase 1: Aggregate score records and PBs
    aggregate_results = identify_aggregate_records_and_pbs(df_round, teg_r, rd_r)
    records_dict.update({
        'aggregate_records': aggregate_results['records'],
        'aggregate_pbs': aggregate_results['personal_bests'],
        'aggregate_worsts': aggregate_results['personal_worsts']
    })

    # All-time worsts
    all_time_worsts = identify_all_time_worsts(df_round, teg_r, rd_r)
    records_dict.update({
        'all_time_worsts': all_time_worsts
    })

    # Phase 2: 9-hole records and PBs (round only)
    nine_hole_results = identify_9hole_records_and_pbs(teg_r, rd_r)
    records_dict.update({
        '9hole_records': nine_hole_results['records'],
        '9hole_pbs': nine_hole_results['personal_bests']
    })

    # Phase 3: Streak records
    streak_results = identify_streak_records(all_data, streaks_df, teg_r, rd_r)
    records_dict.update({
        'streak_records': streak_results['records']
    })

    # Score count records
    score_count_results = identify_score_count_records(all_data, teg_r, rd_r)
    records_dict.update({
        'best_score_counts': score_count_results['best_score_counts'],
        'worst_score_counts': score_count_results['worst_score_counts']
    })

    # Display records and PBs summary
    display_records_and_pbs_summary(records_dict, page_type='Round')

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