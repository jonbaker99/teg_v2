"""Latest/Selected TEG Context Analysis - Compare selected TEG to all other TEGs.

This page displays comprehensive analysis of a selected TEG showing how it compares to
other tournaments. Includes:
- Aggregate score comparison across metrics (Score, Stableford, Gross vs. Par, Net vs. Par)
- Scoring distribution showing player score frequency
- Streak analysis for various achievements
- Records and personal bests achieved in the TEG
- Tournament report with commentary

Corresponds to Streamlit page: streamlit/latest_teg_context.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # nicegui root

from nicegui import ui
import pandas as pd

# Import data loading utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'streamlit'))
from utils import (
    get_ranked_teg_data,
    load_all_data,
    read_file,
    STREAKS_PARQUET,
    read_text_file,
    format_vs_par
)
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    get_teg_options,
    create_metric_tabs_data,
    prepare_teg_context_display
)
from helpers.score_count_processing import count_scores_by_player
from helpers.streak_analysis_processing import get_player_window_streaks
from helpers.records_identification import (
    identify_aggregate_records_and_pbs,
    identify_all_time_worsts,
    identify_streak_records,
    identify_score_count_records,
    display_records_and_pbs_summary
)


def latest_teg_context_content():
    """Display selected TEG in context with comprehensive analysis."""

    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('TEG Context').classes('text-h5 font-bold mt-6')
    ui.label('Shows how latest or selected TEG compares to other TEGs').classes('text-sm text-gray-600')
    ui.separator()

    # ===== DATA LOADING =====
    state = {
        'df_teg': None,
        'all_data': None,
        'streaks_df': None,
        'data_loaded': False,
        'current_teg': None
    }

    def load_data():
        """Load all data once on page load."""
        try:
            state['df_teg'] = get_ranked_teg_data().sort_values(by='TEGNum')
            state['all_data'] = load_all_data(exclude_incomplete_tegs=False)
            state['streaks_df'] = read_file(STREAKS_PARQUET)
            state['data_loaded'] = True

            # Set to latest TEG by default
            teg_options = get_teg_options(state['df_teg'])
            if teg_options:
                state['current_teg'] = teg_options[-1]  # Latest TEG
                teg_selector.value = state['current_teg']

        except Exception as e:
            print(f'Error loading data: {e}')

    # ===== CONTROLS =====
    with ui.row().classes('w-full gap-4 items-center'):
        teg_selector = ui.select([], label='Select TEG').classes('w-48')

        def set_to_latest():
            """Set TEG to latest."""
            teg_options = get_teg_options(state['df_teg'])
            if teg_options:
                state['current_teg'] = teg_options[-1]
                teg_selector.value = state['current_teg']

        ui.button('Latest TEG', on_click=set_to_latest)

    ui.separator()

    # ===== DATA DISPLAY AREA =====
    content_area = ui.card().classes('w-full')

    def display_teg_analysis():
        """Display comprehensive TEG analysis in tabs."""
        try:
            if not state['data_loaded'] or not state['current_teg']:
                return

            teg_t = state['current_teg']
            content_area.clear()

            with content_area:
                with ui.tabs() as main_tabs:
                    # ===== TAB 1: AGGREGATE SCORE =====
                    with ui.tab('Aggregate Score'):
                        metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']
                        metrics, friendly_metrics = create_metric_tabs_data(metrics)
                        name_mapping, _ = get_round_metric_mappings()

                        with ui.tabs() as metric_tabs:
                            for friendly_metric in friendly_metrics:
                                with ui.tab(friendly_metric):
                                    metric = name_mapping.get(friendly_metric, friendly_metric)
                                    context_display = prepare_teg_context_display(
                                        state['df_teg'], teg_t, metric, friendly_metric
                                    )
                                    ui.html(context_display.to_html(
                                        index=False,
                                        justify='left',
                                        classes='datawrapper-table'
                                    ), sanitize=False)

                    # ===== TAB 2: SCORING =====
                    with ui.tab('Scoring'):
                        ui.label('Scoring').classes('text-base font-semibold mb-3')

                        # Scoring type toggle
                        scoring_state = {'type': 'Gross vs Par'}

                        def update_scoring_display():
                            """Update scoring display based on selected type."""
                            scoring_area.clear()
                            with scoring_area:
                                try:
                                    teg_num = int(teg_t.split()[1])
                                    teg_data = state['all_data'][state['all_data']['TEGNum'] == teg_num]

                                    if scoring_state['type'] == 'Gross vs Par':
                                        score_counts = count_scores_by_player(teg_data, field='GrossVP')
                                        score_counts = score_counts.reset_index()
                                        score_counts.columns.name = None

                                        score_counts['GrossVP'] = score_counts['GrossVP'].apply(format_vs_par)
                                        score_counts = score_counts.rename(columns={'GrossVP': 'vs Par'})

                                        player_cols = [col for col in score_counts.columns if col != 'vs Par']
                                        for col in player_cols:
                                            score_counts[col] = score_counts[col].replace(0, '-')
                                    else:
                                        score_counts = count_scores_by_player(teg_data, field='Stableford')
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

                    # ===== TAB 3: STREAKS =====
                    with ui.tab('Streaks'):
                        ui.label('Streaks').classes('text-base font-semibold mb-3')
                        try:
                            teg_num = int(teg_t.split()[1])
                            teg_rounds = state['all_data'][state['all_data']['TEGNum'] == teg_num]['Round'].unique()

                            if len(teg_rounds) > 0:
                                last_round = max(teg_rounds)

                                teg_streaks = get_player_window_streaks(
                                    state['all_data'],
                                    state['streaks_df'],
                                    teg=teg_t,
                                    round_num=last_round
                                )

                                if len(teg_streaks) > 0:
                                    streaks_pivot = teg_streaks.pivot(
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
                                    ui.label('No streak data available for this TEG').classes('text-gray-600')
                            else:
                                ui.label('No data available for this TEG').classes('text-gray-600')
                        except Exception as e:
                            ui.label(f'Error loading streaks: {str(e)}').classes('text-red-600')

                    # ===== TAB 4: RECORDS & PBs =====
                    with ui.tab('Records & PBs'):
                        ui.label('Records & Personal Bests').classes('text-base font-semibold mb-3')
                        try:
                            records_dict = {}

                            aggregate_results = identify_aggregate_records_and_pbs(state['df_teg'], teg_t)
                            records_dict.update({
                                'aggregate_records': aggregate_results['records'],
                                'aggregate_pbs': aggregate_results['personal_bests'],
                                'aggregate_worsts': aggregate_results['personal_worsts']
                            })

                            all_time_worsts = identify_all_time_worsts(state['df_teg'], teg_t)
                            records_dict.update({'all_time_worsts': all_time_worsts})

                            streak_results = identify_streak_records(state['all_data'], state['streaks_df'], teg_t)
                            records_dict.update({'streak_records': streak_results['records']})

                            score_count_results = identify_score_count_records(state['all_data'], teg_t)
                            records_dict.update({
                                'best_score_counts': score_count_results['best_score_counts'],
                                'worst_score_counts': score_count_results['worst_score_counts']
                            })

                            display_records_and_pbs_summary(records_dict, page_type='TEG')
                        except Exception as e:
                            ui.label(f'Error loading records: {str(e)}').classes('text-red-600')
                            print(f'Error in records: {e}')
                            import traceback
                            traceback.print_exc()

                    # ===== TAB 5: REPORT =====
                    with ui.tab('Report'):
                        ui.label('Tournament Report').classes('text-base font-semibold mb-3')
                        try:
                            teg_num = int(teg_t.split()[-1])
                            report_file_path = f"data/commentary/teg_{teg_num}_main_report.md"

                            try:
                                md_text = read_text_file(report_file_path)

                                if teg_num < 8:
                                    ui.label('NB: The TEG Trophy winners before TEG 8 were decided by best net; the report here is written based on Stableford so finishing positions may be inaccurate').classes('text-sm text-gray-600 mb-3')

                                # Render markdown as HTML
                                import importlib.util
                                has_markdown = importlib.util.find_spec("markdown") is not None
                                if has_markdown:
                                    import markdown as md
                                    html_body = md.markdown(md_text, extensions=["extra", "sane_lists", "smarty", "toc"])
                                    full_html = f"<div class='teg-report'>{html_body}</div>"
                                    ui.html(full_html, sanitize=False)
                                else:
                                    ui.label(md_text)
                            except FileNotFoundError:
                                ui.label(f'No report available yet for {teg_t}').classes('text-gray-600')
                            except Exception as report_error:
                                ui.label(f'Error loading report: {str(report_error)}').classes('text-red-600')

                        except Exception as e:
                            ui.label(f'Error in report tab: {str(e)}').classes('text-red-600')

        except Exception as e:
            content_area.clear()
            with content_area:
                ui.label(f'Error loading TEG analysis: {str(e)}').classes('text-red-600')
                print(f'Error in latest_teg_context: {e}')
                import traceback
                traceback.print_exc()

    # ===== EVENT HANDLERS =====
    teg_selector.on_value_change(
        lambda: (
            state.update({'current_teg': teg_selector.value}),
            display_teg_analysis()
        )
    )

    # ===== INITIAL LOAD =====
    load_data()
    if state['data_loaded']:
        teg_options = get_teg_options(state['df_teg'])
        teg_selector.set_options(teg_options)
        if teg_options:
            teg_selector.value = state['current_teg']
            display_teg_analysis()
