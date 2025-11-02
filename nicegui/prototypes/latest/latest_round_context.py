"""Latest/Selected Round Context Analysis - Compare selected round to all other rounds.

This page displays comprehensive analysis of a selected round showing how it compares to
other rounds. Includes:
- Scoreboards with round rankings across metrics (Score, Stableford, Gross vs. Par, Net vs. Par)
- Cumulative performance charts for each metric through the selected round
- Detailed hole-by-hole scorecard with Desktop/Mobile view options
- Round report with commentary
- Scoring distribution showing player score frequency
- Streak analysis for various achievements
- Records and personal bests achieved in the round

Corresponds to Streamlit page: streamlit/latest_round.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd
import plotly.graph_objects as go

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import (
    get_ranked_round_data,
    load_all_data,
    read_file,
    read_text_file,
    STREAKS_PARQUET,
    format_vs_par
)
from make_charts import create_round_graph
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    get_teg_and_round_options,
    create_metric_tabs_data,
    prepare_round_context_display
)
from scorecard_utils import (
    generate_round_comparison_html,
    generate_round_comparison_html_mobile
)
from helpers.score_count_processing import count_scores_by_player
from helpers.streak_analysis_processing import get_player_window_streaks
from helpers.records_identification import (
    identify_aggregate_records_and_pbs,
    identify_all_time_worsts,
    identify_9hole_records_and_pbs,
    identify_streak_records,
    identify_score_count_records,
    display_records_and_pbs_summary
)


def latest_round_context_content():
    """Display selected round in context with comprehensive analysis."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Round Context').classes('text-h5 font-bold mt-6')
    ui.label('Shows how selected round compares to other rounds').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'df_round': None,
        'all_data': None,
        'round_info': None,
        'streaks_df': None,
        'data_loaded': False,
        'current_teg': None,
        'current_round': None
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['df_round'] = get_ranked_round_data().sort_values(by=['TEGNum', 'Round'])
            state['all_data'] = load_all_data(exclude_incomplete_tegs=False)
            state['round_info'] = read_file('data/round_info.csv')
            state['streaks_df'] = read_file(STREAKS_PARQUET)
            state['data_loaded'] = True

            # Set to latest round by default
            teg_options, _ = get_teg_and_round_options(state['df_round'], None)
            if teg_options:
                state['current_teg'] = teg_options[-1]
                _, round_options = get_teg_and_round_options(state['df_round'], state['current_teg'])
                if round_options:
                    state['current_round'] = round_options[-1]

        except Exception as e:
            print(f'Error loading data: {e}')

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        teg_selector = ui.select([], label='Select TEG').classes('w-48')
        round_selector = ui.select([], label='Select Round').classes('w-48')

    ui.separator()

    # ===== COURSE & DATE DISPLAY =====
    info_label = ui.label('').classes('text-base font-semibold')

    def update_round_options():
        """Update available rounds when TEG changes."""
        if not state['current_teg']:
            return

        _, round_options = get_teg_and_round_options(state['df_round'], state['current_teg'])
        round_selector.set_options(round_options)

        if round_options:
            if state['current_round'] in round_options:
                round_selector.value = state['current_round']
            else:
                state['current_round'] = round_options[-1]
                round_selector.value = state['current_round']

    def update_info_label():
        """Update course and date information."""
        if not state['current_teg'] or not state['current_round']:
            info_label.text = ''
            return

        try:
            mask = (state['round_info']["TEG"] == state['current_teg']) & \
                   (state['round_info']["Round"] == state['current_round'])
            if mask.any():
                course = state['round_info'].loc[mask, "Course"].squeeze()
                date = state['round_info'].loc[mask, "Date"].squeeze()
                info_label.text = f"{state['current_teg']} R{state['current_round']} | {course} | {date}"
            else:
                info_label.text = f"{state['current_teg']} R{state['current_round']}"
        except Exception as e:
            info_label.text = f"{state['current_teg']} R{state['current_round']}"

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    def display_round_analysis():
        """Display comprehensive round analysis with button-based section navigation."""
        try:
            if not state['data_loaded'] or not state['current_teg'] or not state['current_round']:
                return

            teg_r = state['current_teg']
            rd_r = state['current_round']
            content_area.clear()

            with content_area:
                ui.code('''
get_ranked_round_data()
load_all_data(exclude_incomplete_tegs=False)
read_file('data/round_info.csv')
read_file(STREAKS_PARQUET)
create_metric_tabs_data(metrics)
prepare_round_context_display(df_round, teg_r, rd_r, metric, friendly_metric)
create_round_graph(all_data, chosen_teg=teg_r, chosen_round=rd_r, y_series=cum_metric)
generate_round_comparison_html(teg_num, rd_r)
count_scores_by_player(round_data, field='GrossVP')
get_player_window_streaks(all_data, streaks_df, teg=teg_r, round_num=rd_r)
identify_aggregate_records_and_pbs(df_round, teg_r, rd_r)
''', language='python').classes('mb-4')

                # ===== SECTION SELECTOR =====
                section_state = {'current': 'scoreboards'}

                def set_section(section_name):
                    section_state['current'] = section_name

                # Button bar to select section
                with ui.row().classes('gap-2 mb-4 flex-wrap'):
                    ui.button('Scoreboards', on_click=lambda: set_section('scoreboards')).props('flat')
                    ui.button('Scorecard', on_click=lambda: set_section('scorecard')).props('flat')
                    ui.button('Report', on_click=lambda: set_section('report')).props('flat')
                    ui.button('Scoring', on_click=lambda: set_section('scoring')).props('flat')
                    ui.button('Streaks', on_click=lambda: set_section('streaks')).props('flat')
                    ui.button('Records & PBs', on_click=lambda: set_section('records')).props('flat')

                # ===== SECTION 1: SCOREBOARDS =====
                scoreboards_card = ui.card().classes('w-full')
                scoreboards_card.bind_visibility_from(section_state, 'current', lambda v: v == 'scoreboards')

                with scoreboards_card:
                    metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']
                    metrics, friendly_metrics = create_metric_tabs_data(metrics)
                    name_mapping, _ = get_round_metric_mappings()

                    with ui.tabs() as metric_tabs:
                        for friendly_metric in friendly_metrics:
                            with ui.tab(friendly_metric):
                                # Context table
                                context_display = prepare_round_context_display(
                                    state['df_round'], teg_r, rd_r,
                                    name_mapping.get(friendly_metric, friendly_metric),
                                    friendly_metric
                                )
                                ui.html(context_display.to_html(
                                    index=False,
                                    justify='left',
                                    classes='datawrapper-table'
                                ), sanitize=False)

                                # Cumulative chart
                                ui.label(f'Cumulative {friendly_metric} through round').classes(
                                    'text-base font-semibold mt-6 mb-3'
                                )

                                try:
                                    metric = name_mapping.get(friendly_metric, friendly_metric)
                                    cum_metric = f'{metric} Cum Round'
                                    fig_rd = create_round_graph(
                                        state['all_data'],
                                        chosen_teg=teg_r,
                                        chosen_round=rd_r,
                                        y_series=cum_metric,
                                        title=friendly_metric,
                                        y_axis_label=f'Cumulative {friendly_metric}'
                                    )

                                    fig_rd.update_traces(
                                        mode="lines+markers",
                                        marker=dict(symbol="circle", size=6, line=dict(width=1, color="white"))
                                    )

                                    fig_rd.update_xaxes(
                                        visible=True,
                                        showline=True,
                                        linewidth=1,
                                        linecolor="#ccc",
                                        ticks="outside",
                                        tickmode="linear",
                                        tick0=1,
                                        dtick=1,
                                        title_text="Hole",
                                        range=[0.5, 18.5]
                                    )

                                    ui.plotly(fig_rd).classes('w-full')
                                except Exception as e:
                                    ui.label(f'Error creating chart: {str(e)}').classes('text-red-600')

                # ===== SECTION 2: SCORECARD =====
                scorecard_card = ui.card().classes('w-full')
                scorecard_card.bind_visibility_from(section_state, 'current', lambda v: v == 'scorecard')

                with scorecard_card:
                    ui.label('Scorecard').classes('text-base font-semibold mb-3')

                    scorecard_state = {'view': 'Desktop'}

                    def update_scorecard():
                        """Update scorecard view."""
                        scorecard_area.clear()
                        with scorecard_area:
                            try:
                                teg_num = int(teg_r.split()[1])

                                if scorecard_state['view'] == 'Desktop':
                                    scorecard_html = generate_round_comparison_html(teg_num, rd_r)
                                else:
                                    scorecard_html = generate_round_comparison_html_mobile(teg_num, rd_r)

                                ui.html(scorecard_html, sanitize=False)
                            except Exception as e:
                                ui.label(f'Error loading scorecard: {str(e)}').classes('text-red-600')

                    with ui.row().classes('w-full gap-4 items-center'):
                        ui.label('Scorecard view:').classes('font-semibold')
                        view_toggle = ui.toggle(
                            ['Desktop', 'Mobile'],
                            value='Desktop'
                        )
                        view_toggle.on_value_change(
                            lambda: (
                                scorecard_state.update({'view': view_toggle.value}),
                                update_scorecard()
                            )
                        )

                    scorecard_area = ui.card().classes('w-full')
                    update_scorecard()

                # ===== SECTION 3: REPORT =====
                report_card = ui.card().classes('w-full')
                report_card.bind_visibility_from(section_state, 'current', lambda v: v == 'report')

                with report_card:
                    ui.label('Round Report').classes('text-base font-semibold mb-3')
                    try:
                        teg_num = int(teg_r.split()[1])

                        report_path_new = f"data/commentary/round_reports/TEG{teg_num}_R{rd_r}_report.md"
                        report_path_old = f"data/commentary/round_reports/teg_{teg_num}_round_{rd_r}_report.md"

                        report_content = None
                        try:
                            report_content = read_text_file(report_path_new)
                        except FileNotFoundError:
                            try:
                                report_content = read_text_file(report_path_old)
                            except FileNotFoundError:
                                pass

                        if report_content:
                            import importlib.util
                            has_markdown = importlib.util.find_spec("markdown") is not None
                            if has_markdown:
                                import markdown as md
                                html_body = md.markdown(report_content, extensions=["extra", "sane_lists", "smarty", "toc"])
                                full_html = f"<div class='teg-report'>{html_body}</div>"
                                ui.html(full_html, sanitize=False)
                            else:
                                ui.label(report_content)
                        else:
                            ui.label(f'No round report available for {teg_r} Round {rd_r}').classes('text-gray-600')

                    except Exception as e:
                        ui.label(f'Error loading report: {str(e)}').classes('text-red-600')

                # ===== SECTION 4: SCORING =====
                scoring_card = ui.card().classes('w-full')
                scoring_card.bind_visibility_from(section_state, 'current', lambda v: v == 'scoring')

                with scoring_card:
                    ui.label('Scoring').classes('text-base font-semibold mb-3')

                    scoring_state = {'type': 'Gross vs Par'}

                    def update_scoring_display():
                        """Update scoring display based on selected type."""
                        scoring_area.clear()
                        with scoring_area:
                            try:
                                teg_num = int(teg_r.split()[1])
                                round_data = state['all_data'][
                                    (state['all_data']['TEGNum'] == teg_num) &
                                    (state['all_data']['Round'] == rd_r)
                                ]

                                if scoring_state['type'] == 'Gross vs Par':
                                    score_counts = count_scores_by_player(round_data, field='GrossVP')
                                    score_counts = score_counts.reset_index()
                                    score_counts.columns.name = None

                                    score_counts['GrossVP'] = score_counts['GrossVP'].apply(format_vs_par)
                                    score_counts = score_counts.rename(columns={'GrossVP': 'vs Par'})

                                    player_cols = [col for col in score_counts.columns if col != 'vs Par']
                                    for col in player_cols:
                                        score_counts[col] = score_counts[col].replace(0, '-')
                                else:
                                    score_counts = count_scores_by_player(round_data, field='Stableford')
                                    score_counts = score_counts.sort_index(ascending=False)
                                    score_counts = score_counts.reset_index()
                                    score_counts.columns.name = None

                                    score_counts['Stableford'] = score_counts['Stableford'].astype(int)
                                    player_cols = [col for col in score_counts.columns if col != 'Stableford']
                                    for col in player_cols:
                                        score_counts[col] = score_counts[col].replace(0, '-')

                                ui.html(score_counts.to_html(
                                    index=False,
                                    justify='left',
                                    classes='datawrapper-table'
                                ), sanitize=False)
                            except Exception as e:
                                ui.label(f'Error loading scoring: {str(e)}').classes('text-red-600')

                    with ui.row().classes('w-full gap-4 items-center'):
                        ui.label('Scoring type:').classes('font-semibold')
                        scoring_toggle = ui.toggle(
                            ['Gross vs Par', 'Stableford'],
                            value='Gross vs Par'
                        )
                        scoring_toggle.on_value_change(
                            lambda: (
                                scoring_state.update({'type': scoring_toggle.value}),
                                update_scoring_display()
                            )
                        )

                    scoring_area = ui.card().classes('w-full')
                    update_scoring_display()

                # ===== SECTION 5: STREAKS =====
                streaks_card = ui.card().classes('w-full')
                streaks_card.bind_visibility_from(section_state, 'current', lambda v: v == 'streaks')

                with streaks_card:
                    ui.label('Streaks').classes('text-base font-semibold mb-3')
                    try:
                        round_streaks = get_player_window_streaks(
                            state['all_data'],
                            state['streaks_df'],
                            teg=teg_r,
                            round_num=rd_r
                        )

                        if len(round_streaks) > 0:
                            streaks_pivot = round_streaks.pivot(
                                index='Streak Type',
                                columns='Player',
                                values='Max Streak'
                            )
                            streaks_pivot = streaks_pivot.reset_index()
                            streaks_pivot.columns.name = None

                            streak_mapping = {
                                'Eagles': 'Eagles',
                                'Birdies': 'Birdies',
                                'Pars or Better': 'Pars',
                                'No +2s': 'Bogeys',
                                'Over Par': 'Over par',
                                'TBPs': 'TBPs'
                            }

                            streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'].isin(streak_mapping.keys())].copy()
                            streaks_pivot['Streak Type'] = streaks_pivot['Streak Type'].map(streak_mapping)

                            desired_order = ['Eagles', 'Birdies', 'Pars', 'Bogeys', 'Over par', 'TBPs']
                            streaks_pivot['_order'] = streaks_pivot['Streak Type'].map(
                                {s: i for i, s in enumerate(desired_order)}
                            )
                            streaks_pivot = streaks_pivot.sort_values('_order').drop('_order', axis=1)

                            player_cols = [col for col in streaks_pivot.columns if col != 'Streak Type']

                            if 'Eagles' in streaks_pivot['Streak Type'].values:
                                eagles_max = streaks_pivot[streaks_pivot['Streak Type'] == 'Eagles'][player_cols].max(axis=1).iloc[0]
                                if eagles_max == 0:
                                    streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'] != 'Eagles']

                            if 'Birdies' in streaks_pivot['Streak Type'].values:
                                birdies_max = streaks_pivot[streaks_pivot['Streak Type'] == 'Birdies'][player_cols].max(axis=1).iloc[0]
                                if birdies_max == 0:
                                    streaks_pivot = streaks_pivot[streaks_pivot['Streak Type'] != 'Birdies']

                            ui.html(streaks_pivot.to_html(
                                index=False,
                                justify='left',
                                classes='datawrapper-table'
                            ), sanitize=False)
                            ui.label('Eagles / birdies / par / bogeys are all \'or better\'').classes('text-sm text-gray-600 mt-3')
                        else:
                            ui.label('No streak data available for this round').classes('text-gray-600')
                    except Exception as e:
                        ui.label(f'Error loading streaks: {str(e)}').classes('text-red-600')

                # ===== SECTION 6: RECORDS & PBs =====
                records_card = ui.card().classes('w-full')
                records_card.bind_visibility_from(section_state, 'current', lambda v: v == 'records')

                with records_card:
                    ui.label('Records & Personal Bests').classes('text-base font-semibold mb-3')
                    try:
                        records_dict = {}

                        aggregate_results = identify_aggregate_records_and_pbs(state['df_round'], teg_r, rd_r)
                        records_dict.update({
                            'aggregate_records': aggregate_results['records'],
                            'aggregate_pbs': aggregate_results['personal_bests'],
                            'aggregate_worsts': aggregate_results['personal_worsts']
                        })

                        all_time_worsts = identify_all_time_worsts(state['df_round'], teg_r, rd_r)
                        records_dict.update({'all_time_worsts': all_time_worsts})

                        nine_hole_results = identify_9hole_records_and_pbs(teg_r, rd_r)
                        records_dict.update({
                            '9hole_records': nine_hole_results['records'],
                            '9hole_pbs': nine_hole_results['personal_bests']
                        })

                        streak_results = identify_streak_records(state['all_data'], state['streaks_df'], teg_r, rd_r)
                        records_dict.update({'streak_records': streak_results['records']})

                        score_count_results = identify_score_count_records(state['all_data'], teg_r, rd_r)
                        records_dict.update({
                            'best_score_counts': score_count_results['best_score_counts'],
                            'worst_score_counts': score_count_results['worst_score_counts']
                        })

                        display_records_and_pbs_summary(records_dict, page_type='Round')
                    except Exception as e:
                        ui.label(f'Error loading records: {str(e)}').classes('text-red-600')
                        print(f'Error in records: {e}')
                        import traceback
                        traceback.print_exc()

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading round analysis: {str(e)}').classes('text-red-600')
                print(f'Error in latest_round_context: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    def handle_teg_change():
        """Handle TEG selection change."""
        state['current_teg'] = teg_selector.value
        update_round_options()
        update_info_label()
        display_round_analysis()

    def handle_round_change():
        """Handle round selection change."""
        state['current_round'] = round_selector.value
        update_info_label()
        display_round_analysis()

    teg_selector.on_value_change(handle_teg_change)
    round_selector.on_value_change(handle_round_change)

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded']:
        teg_options, _ = get_teg_and_round_options(state['df_round'], None)
        teg_selector.set_options(teg_options)
        if teg_options and state['current_teg']:
            teg_selector.value = state['current_teg']
            update_round_options()
            update_info_label()
            display_round_analysis()
