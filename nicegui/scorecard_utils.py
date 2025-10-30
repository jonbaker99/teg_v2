"""NiceGUI Scorecard Generation Utilities.

This module provides functions to generate golf scorecard tables for display in NiceGUI.
It adapts the Streamlit scorecard builders to return only the core table HTML without
title/header elements (those are handled by NiceGUI's ui.label() instead).

Functions return only the <table> HTML, ready to be displayed with ui.html().
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # project root
sys.path.insert(0, str(Path(__file__).parent.parent / 'streamlit'))

import pandas as pd
from utils import get_scorecard_data, get_teg_metadata, format_date_for_scorecard


def generate_single_round_table(player_code: str, teg_num: int, round_num: int) -> str:
    """Generate HTML table for single player, single round scorecard (DESKTOP).

    Args:
        player_code: Player identifier (e.g., 'AW', 'JB')
        teg_num: Tournament number
        round_num: Round number (1-4)

    Returns:
        HTML string containing only the scorecard table (no headers/titles)
    """
    try:
        # Load data
        df = get_scorecard_data(teg_num, round_num, player_code)

        if len(df) != 18:
            return f"<div class='scorecard-container'><p>Error: Expected 18 holes, found {len(df)} holes.</p></div>"

        # Calculate totals
        front_9 = df[df['Hole'] <= 9]
        back_9 = df[df['Hole'] > 9]

        front_totals = {
            'PAR': int(front_9['PAR'].sum()),
            'Sc': int(front_9['Sc'].sum()),
            'Stableford': int(front_9['Stableford'].sum())
        }

        back_totals = {
            'PAR': int(back_9['PAR'].sum()),
            'Sc': int(back_9['Sc'].sum()),
            'Stableford': int(back_9['Stableford'].sum())
        }

        total_totals = {
            'PAR': int(df['PAR'].sum()),
            'Sc': int(df['Sc'].sum()),
            'Stableford': int(df['Stableford'].sum())
        }

        # Build HTML - only table, no header/title divs
        html_parts = []
        html_parts.append('<table class="scorecard-table">')

        # Header section
        html_parts.append('<thead>')

        # Hole numbers row
        html_parts.append('<tr>')
        html_parts.append('<th class="label-column hole-header">Hole</th>')
        for hole in range(1, 10):
            html_parts.append(f'<th class="hole-header">{hole}</th>')
        html_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
        for hole in range(10, 19):
            html_parts.append(f'<th class="hole-header">{hole}</th>')
        html_parts.append('<th class="hole-header totals">IN</th>')
        html_parts.append('<th class="hole-header totals">TOTAL</th>')
        html_parts.append('</tr>')

        # PAR row
        html_parts.append('<tr>')
        html_parts.append('<th class="label-column par-header">PAR</th>')
        for hole in range(1, 10):
            par_val = int(df[df['Hole'] == hole]['PAR'].iloc[0])
            html_parts.append(f'<th class="par-header">{par_val}</th>')
        html_parts.append(f'<th class="totals front-back-divider par-header">{front_totals["PAR"]}</th>')
        for hole in range(10, 19):
            par_val = int(df[df['Hole'] == hole]['PAR'].iloc[0])
            html_parts.append(f'<th class="par-header">{par_val}</th>')
        html_parts.append(f'<th class="totals par-header">{back_totals["PAR"]}</th>')
        html_parts.append(f'<th class="totals par-header">{total_totals["PAR"]}</th>')
        html_parts.append('</tr>')

        html_parts.append('</thead>')

        # Body section
        html_parts.append('<tbody>')

        # Score row
        html_parts.append('<tr>')
        html_parts.append('<td class="label-column">Score</td>')
        for hole in range(1, 10):
            hole_data = df[df['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

        html_parts.append(f'<td class="totals front-back-divider">{front_totals["Sc"]}</td>')

        for hole in range(10, 19):
            hole_data = df[df['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        html_parts.append(f'<td class="totals">{back_totals["Sc"]}</td>')
        html_parts.append(f'<td class="totals">{total_totals["Sc"]}</td>')
        html_parts.append('</tr>')

        # Stableford row
        html_parts.append('<tr>')
        html_parts.append('<td class="label-column">Stableford</td>')
        for hole in range(1, 10):
            hole_data = df[df['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        html_parts.append(f'<td class="totals front-back-divider">{front_totals["Stableford"]}</td>')
        for hole in range(10, 19):
            hole_data = df[df['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        html_parts.append(f'<td class="totals">{back_totals["Stableford"]}</td>')
        html_parts.append(f'<td class="totals">{total_totals["Stableford"]}</td>')
        html_parts.append('</tr>')

        html_parts.append('</tbody>')
        html_parts.append('</table>')

        return ''.join(html_parts)

    except Exception as e:
        return f"<div class='scorecard-container'><p>Error: {str(e)}</p></div>"


def generate_tournament_table(player_code: str, teg_num: int) -> tuple:
    """Generate HTML tables for single player tournament view (all rounds) (DESKTOP).

    Returns tuple of (gross_table_html, stableford_table_html) for display as separate tables.

    Args:
        player_code: Player identifier
        teg_num: Tournament number

    Returns:
        Tuple of (gross_scores_html, stableford_points_html)
    """
    try:
        # Load data
        player_data = get_scorecard_data(teg_num, player_code=player_code)

        if player_data.empty:
            error_msg = f"<div class='scorecard-container'><p>Error: No data found for player {player_code} in TEG {teg_num}.</p></div>"
            return error_msg, error_msg

        rounds = sorted(player_data['Round'].unique())

        # Build Gross Scores table
        gross_parts = []
        gross_parts.append('<table class="scorecard-table">')

        gross_parts.append('<thead>')
        gross_parts.append('<tr>')
        gross_parts.append('<th class="round-label">Round</th>')
        for hole in range(1, 10):
            gross_parts.append(f'<th>{hole}</th>')
        gross_parts.append('<th class="totals front-back-divider">OUT</th>')
        for hole in range(10, 19):
            gross_parts.append(f'<th>{hole}</th>')
        gross_parts.append('<th class="totals">IN</th>')
        gross_parts.append('<th class="totals">TOTAL</th>')
        gross_parts.append('</tr>')
        gross_parts.append('</thead>')

        gross_parts.append('<tbody>')
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num].sort_values('Hole')

            # Calculate totals
            front_total = int(round_data[round_data['Hole'] <= 9]['Sc'].sum())
            back_total = int(round_data[round_data['Hole'] > 9]['Sc'].sum())
            total_score = int(round_data['Sc'].sum())

            gross_parts.append('<tr>')
            gross_parts.append(f'<td class="round-label">Round {round_num}</td>')

            # Front 9
            for hole in range(1, 10):
                hole_data = round_data[round_data['Hole'] == hole].iloc[0]
                vs_par = int(hole_data['GrossVP'])
                score = int(hole_data['Sc'])
                gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

            gross_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

            # Back 9
            for hole in range(10, 19):
                hole_data = round_data[round_data['Hole'] == hole].iloc[0]
                vs_par = int(hole_data['GrossVP'])
                score = int(hole_data['Sc'])
                gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

            gross_parts.append(f'<td class="totals">{back_total}</td>')
            gross_parts.append(f'<td class="totals">{total_score}</td>')
            gross_parts.append('</tr>')

        gross_parts.append('</tbody>')
        gross_parts.append('</table>')

        # Build Stableford Points table
        stableford_parts = []
        stableford_parts.append('<table class="scorecard-table">')

        stableford_parts.append('<thead>')
        stableford_parts.append('<tr>')
        stableford_parts.append('<th class="round-label">Round</th>')
        for hole in range(1, 10):
            stableford_parts.append(f'<th>{hole}</th>')
        stableford_parts.append('<th class="totals front-back-divider">OUT</th>')
        for hole in range(10, 19):
            stableford_parts.append(f'<th>{hole}</th>')
        stableford_parts.append('<th class="totals">IN</th>')
        stableford_parts.append('<th class="totals">TOTAL</th>')
        stableford_parts.append('</tr>')
        stableford_parts.append('</thead>')

        stableford_parts.append('<tbody>')
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num].sort_values('Hole')

            # Calculate totals
            front_total = int(round_data[round_data['Hole'] <= 9]['Stableford'].sum())
            back_total = int(round_data[round_data['Hole'] > 9]['Stableford'].sum())
            total_stableford = int(round_data['Stableford'].sum())

            stableford_parts.append('<tr>')
            stableford_parts.append(f'<td class="round-label">Round {round_num}</td>')

            # Front 9
            for hole in range(1, 10):
                hole_data = round_data[round_data['Hole'] == hole].iloc[0]
                stableford = int(hole_data['Stableford'])
                stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

            stableford_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

            # Back 9
            for hole in range(10, 19):
                hole_data = round_data[round_data['Hole'] == hole].iloc[0]
                stableford = int(hole_data['Stableford'])
                stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

            stableford_parts.append(f'<td class="totals">{back_total}</td>')
            stableford_parts.append(f'<td class="totals">{total_stableford}</td>')
            stableford_parts.append('</tr>')

        stableford_parts.append('</tbody>')
        stableford_parts.append('</table>')

        return ''.join(gross_parts), ''.join(stableford_parts)

    except Exception as e:
        error_msg = f"<div class='scorecard-container'><p>Error: {str(e)}</p></div>"
        return error_msg, error_msg


def generate_round_comparison_table(teg_num: int, round_num: int) -> tuple:
    """Generate HTML tables for multi-player round comparison (DESKTOP).

    Returns tuple of (gross_table_html, stableford_table_html) for display as separate tables.

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        Tuple of (gross_scores_html, stableford_points_html)
    """
    try:
        # Load data
        round_data = get_scorecard_data(teg_num, round_num)

        if round_data.empty:
            error_msg = f"<div class='scorecard-container'><p>Error: No data found for TEG {teg_num} Round {round_num}.</p></div>"
            return error_msg, error_msg

        players = round_data['Pl'].unique()

        # Sort players by total score (ascending)
        player_totals = []
        for player in players:
            player_data = round_data[round_data['Pl'] == player]
            total_score = int(player_data['Sc'].sum())
            player_name = player_data['Player'].iloc[0]
            player_totals.append((total_score, player, player_name))

        player_totals.sort(key=lambda x: x[0])  # Sort by score
        sorted_players = [(player, name) for _, player, name in player_totals]

        # Calculate PAR totals
        first_player_data = round_data[round_data['Pl'] == players[0]].sort_values('Hole')
        front_par_total = int(first_player_data[first_player_data['Hole'] <= 9]['PAR'].sum())
        back_par_total = int(first_player_data[first_player_data['Hole'] > 9]['PAR'].sum())
        total_par = int(first_player_data['PAR'].sum())

        # Build Gross Scores table
        gross_parts = []
        gross_parts.append('<table class="scorecard-table">')

        gross_parts.append('<thead>')

        # Row 1: Hole numbers
        gross_parts.append('<tr>')
        gross_parts.append('<th class="player-label hole-header">Player</th>')
        for hole in range(1, 10):
            gross_parts.append(f'<th class="hole-header">{hole}</th>')
        gross_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
        for hole in range(10, 19):
            gross_parts.append(f'<th class="hole-header">{hole}</th>')
        gross_parts.append('<th class="hole-header totals">IN</th>')
        gross_parts.append('<th class="hole-header totals">TOTAL</th>')
        gross_parts.append('</tr>')

        # Row 2: PAR values
        gross_parts.append('<tr>')
        gross_parts.append('<th class="player-label par-header">PAR</th>')
        for hole in range(1, 10):
            par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
            gross_parts.append(f'<th class="par-header">{par_val}</th>')
        gross_parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
        for hole in range(10, 19):
            par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
            gross_parts.append(f'<th class="par-header">{par_val}</th>')
        gross_parts.append(f'<th class="totals par-header">{back_par_total}</th>')
        gross_parts.append(f'<th class="totals par-header">{total_par}</th>')
        gross_parts.append('</tr>')

        gross_parts.append('</thead>')

        # Body - one row per player
        gross_parts.append('<tbody>')
        for player_code, player_name in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')

            # Calculate totals
            front_total = int(player_data[player_data['Hole'] <= 9]['Sc'].sum())
            back_total = int(player_data[player_data['Hole'] > 9]['Sc'].sum())
            total_score = int(player_data['Sc'].sum())

            gross_parts.append('<tr>')
            gross_parts.append(f'<td class="player-label">{player_name}</td>')

            # Front 9
            for hole in range(1, 10):
                hole_data = player_data[player_data['Hole'] == hole].iloc[0]
                vs_par = int(hole_data['GrossVP'])
                score = int(hole_data['Sc'])
                gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

            gross_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

            # Back 9
            for hole in range(10, 19):
                hole_data = player_data[player_data['Hole'] == hole].iloc[0]
                vs_par = int(hole_data['GrossVP'])
                score = int(hole_data['Sc'])
                gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

            gross_parts.append(f'<td class="totals">{back_total}</td>')
            gross_parts.append(f'<td class="totals">{total_score}</td>')
            gross_parts.append('</tr>')

        gross_parts.append('</tbody>')
        gross_parts.append('</table>')

        # Build Stableford Points table
        stableford_parts = []
        stableford_parts.append('<table class="scorecard-table">')

        stableford_parts.append('<thead>')

        # Row 1: Hole numbers
        stableford_parts.append('<tr>')
        stableford_parts.append('<th class="player-label hole-header">Player</th>')
        for hole in range(1, 10):
            stableford_parts.append(f'<th class="hole-header">{hole}</th>')
        stableford_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
        for hole in range(10, 19):
            stableford_parts.append(f'<th class="hole-header">{hole}</th>')
        stableford_parts.append('<th class="hole-header totals">IN</th>')
        stableford_parts.append('<th class="hole-header totals">TOTAL</th>')
        stableford_parts.append('</tr>')

        # Row 2: PAR values
        stableford_parts.append('<tr>')
        stableford_parts.append('<th class="player-label par-header">PAR</th>')
        for hole in range(1, 10):
            par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
            stableford_parts.append(f'<th class="par-header">{par_val}</th>')
        stableford_parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
        for hole in range(10, 19):
            par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
            stableford_parts.append(f'<th class="par-header">{par_val}</th>')
        stableford_parts.append(f'<th class="totals par-header">{back_par_total}</th>')
        stableford_parts.append(f'<th class="totals par-header">{total_par}</th>')
        stableford_parts.append('</tr>')

        stableford_parts.append('</thead>')

        # Body - Stableford scores
        stableford_parts.append('<tbody>')
        for player_code, player_name in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')

            # Calculate totals
            front_total = int(player_data[player_data['Hole'] <= 9]['Stableford'].sum())
            back_total = int(player_data[player_data['Hole'] > 9]['Stableford'].sum())
            total_stableford = int(player_data['Stableford'].sum())

            stableford_parts.append('<tr>')
            stableford_parts.append(f'<td class="player-label">{player_name}</td>')

            # Front 9
            for hole in range(1, 10):
                hole_data = player_data[player_data['Hole'] == hole].iloc[0]
                stableford = int(hole_data['Stableford'])
                stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

            stableford_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

            # Back 9
            for hole in range(10, 19):
                hole_data = player_data[player_data['Hole'] == hole].iloc[0]
                stableford = int(hole_data['Stableford'])
                stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

            stableford_parts.append(f'<td class="totals">{back_total}</td>')
            stableford_parts.append(f'<td class="totals">{total_stableford}</td>')
            stableford_parts.append('</tr>')

        stableford_parts.append('</tbody>')
        stableford_parts.append('</table>')

        return ''.join(gross_parts), ''.join(stableford_parts)

    except Exception as e:
        error_msg = f"<div class='scorecard-container'><p>Error: {str(e)}</p></div>"
        return error_msg, error_msg


# ============================================================================
# MOBILE VERSIONS (3 functions)
# ============================================================================

def generate_single_round_table_mobile(player_code: str, teg_num: int, round_num: int) -> str:
    """Generate HTML table for single player, single round scorecard (MOBILE).

    Args:
        player_code: Player identifier
        teg_num: Tournament number
        round_num: Round number

    Returns:
        HTML string containing only the mobile scorecard table
    """
    try:
        # Load data
        df = get_scorecard_data(teg_num, round_num, player_code)

        if len(df) != 18:
            return f"<div class='scorecard-container-mobile'><p>Error: Expected 18 holes, found {len(df)} holes.</p></div>"

        # Calculate totals
        front_9 = df[df['Hole'] <= 9]
        back_9 = df[df['Hole'] > 9]

        front_totals = {
            'PAR': int(front_9['PAR'].sum()),
            'Sc': int(front_9['Sc'].sum()),
            'Stableford': int(front_9['Stableford'].sum())
        }

        back_totals = {
            'PAR': int(back_9['PAR'].sum()),
            'Sc': int(back_9['Sc'].sum()),
            'Stableford': int(back_9['Stableford'].sum())
        }

        total_totals = {
            'PAR': int(df['PAR'].sum()),
            'Sc': int(df['Sc'].sum()),
            'Stableford': int(df['Stableford'].sum())
        }

        # Build mobile HTML - holes as rows instead of columns
        html_parts = []
        html_parts.append('<table class="scorecard-table-mobile layout-mobile-single-round">')

        html_parts.append('<thead>')
        html_parts.append('<tr>')
        html_parts.append('<th class="hole-label-mobile">Hole</th>')
        html_parts.append('<th class="player-header-mobile">PAR</th>')
        html_parts.append('<th class="player-header-mobile">Score</th>')
        html_parts.append('<th class="player-header-mobile">Stbl</th>')
        html_parts.append('</tr>')
        html_parts.append('</thead>')

        html_parts.append('<tbody>')

        # Data rows - one per hole
        for hole in range(1, 19):
            hole_data = df[df['Hole'] == hole].iloc[0]
            par = int(hole_data['PAR'])
            score = int(hole_data['Sc'])
            stableford = int(hole_data['Stableford'])
            vs_par = int(hole_data['GrossVP'])

            html_parts.append('<tr>')
            html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
            html_parts.append(f'<td class="player-header-mobile">{par}</td>')
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
            html_parts.append('</tr>')

            # Add front/back divider
            if hole == 9:
                html_parts.append('<tr>')
                html_parts.append(f'<td class="hole-label-mobile">OUT</td>')
                html_parts.append(f'<td class="player-header-mobile">{front_totals["PAR"]}</td>')
                html_parts.append(f'<td class="totals-mobile">{front_totals["Sc"]}</td>')
                html_parts.append(f'<td class="totals-mobile">{front_totals["Stableford"]}</td>')
                html_parts.append('</tr>')

        # Totals row
        html_parts.append('<tr>')
        html_parts.append('<td class="hole-label-mobile">TOTAL</td>')
        html_parts.append(f'<td class="player-header-mobile">{total_totals["PAR"]}</td>')
        html_parts.append(f'<td class="totals-mobile">{total_totals["Sc"]}</td>')
        html_parts.append(f'<td class="totals-mobile">{total_totals["Stableford"]}</td>')
        html_parts.append('</tr>')

        html_parts.append('</tbody>')
        html_parts.append('</table>')

        return ''.join(html_parts)

    except Exception as e:
        return f"<div class='scorecard-container-mobile'><p>Error: {str(e)}</p></div>"


def generate_tournament_table_mobile(player_code: str, teg_num: int) -> tuple:
    """Generate HTML tables for single player tournament view (MOBILE - all rounds).

    Returns tuple of (gross_table_html, stableford_table_html).

    Args:
        player_code: Player identifier
        teg_num: Tournament number

    Returns:
        Tuple of (gross_scores_html, stableford_points_html)
    """
    try:
        # Load data
        player_data = get_scorecard_data(teg_num, player_code=player_code)

        if player_data.empty:
            error_msg = f"<div class='scorecard-container-mobile'><p>Error: No data found for player {player_code} in TEG {teg_num}.</p></div>"
            return error_msg, error_msg

        rounds = sorted(player_data['Round'].unique())

        # Build Gross Scores table
        gross_parts = []
        gross_parts.append('<table class="scorecard-table-mobile layout-mobile-multi-round">')

        gross_parts.append('<thead>')
        gross_parts.append('<tr>')
        gross_parts.append('<th class="hole-label-mobile">Hole</th>')
        for round_num in rounds:
            gross_parts.append(f'<th class="round-header-mobile">R{round_num}</th>')
        gross_parts.append('</tr>')
        gross_parts.append('</thead>')

        gross_parts.append('<tbody>')

        # One row per hole showing all rounds
        for hole in range(1, 19):
            gross_parts.append('<tr>')
            gross_parts.append(f'<td class="hole-label-mobile">{hole}</td>')

            for round_num in rounds:
                round_data = player_data[player_data['Round'] == round_num]
                hole_data = round_data[round_data['Hole'] == hole]

                if not hole_data.empty:
                    vs_par = int(hole_data.iloc[0]['GrossVP'])
                    score = int(hole_data.iloc[0]['Sc'])
                    gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
                else:
                    gross_parts.append('<td></td>')

            gross_parts.append('</tr>')

            # Add OUT divider
            if hole == 9:
                gross_parts.append('<tr>')
                gross_parts.append('<td class="hole-label-mobile">OUT</td>')
                for round_num in rounds:
                    round_data = player_data[player_data['Round'] == round_num]
                    front_total = int(round_data[round_data['Hole'] <= 9]['Sc'].sum())
                    gross_parts.append(f'<td class="totals-mobile">{front_total}</td>')
                gross_parts.append('</tr>')

        # Totals row
        gross_parts.append('<tr>')
        gross_parts.append('<td class="hole-label-mobile">TOTAL</td>')
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            total_score = int(round_data['Sc'].sum())
            gross_parts.append(f'<td class="totals-mobile">{total_score}</td>')
        gross_parts.append('</tr>')

        gross_parts.append('</tbody>')
        gross_parts.append('</table>')

        # Build Stableford Points table (similar structure)
        stableford_parts = []
        stableford_parts.append('<table class="scorecard-table-mobile layout-mobile-multi-round">')

        stableford_parts.append('<thead>')
        stableford_parts.append('<tr>')
        stableford_parts.append('<th class="hole-label-mobile">Hole</th>')
        for round_num in rounds:
            stableford_parts.append(f'<th class="round-header-mobile">R{round_num}</th>')
        stableford_parts.append('</tr>')
        stableford_parts.append('</thead>')

        stableford_parts.append('<tbody>')

        for hole in range(1, 19):
            stableford_parts.append('<tr>')
            stableford_parts.append(f'<td class="hole-label-mobile">{hole}</td>')

            for round_num in rounds:
                round_data = player_data[player_data['Round'] == round_num]
                hole_data = round_data[round_data['Hole'] == hole]

                if not hole_data.empty:
                    stableford = int(hole_data.iloc[0]['Stableford'])
                    stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
                else:
                    stableford_parts.append('<td></td>')

            stableford_parts.append('</tr>')

            if hole == 9:
                stableford_parts.append('<tr>')
                stableford_parts.append('<td class="hole-label-mobile">OUT</td>')
                for round_num in rounds:
                    round_data = player_data[player_data['Round'] == round_num]
                    front_total = int(round_data[round_data['Hole'] <= 9]['Stableford'].sum())
                    stableford_parts.append(f'<td class="totals-mobile">{front_total}</td>')
                stableford_parts.append('</tr>')

        stableford_parts.append('<tr>')
        stableford_parts.append('<td class="hole-label-mobile">TOTAL</td>')
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            total_stableford = int(round_data['Stableford'].sum())
            stableford_parts.append(f'<td class="totals-mobile">{total_stableford}</td>')
        stableford_parts.append('</tr>')

        stableford_parts.append('</tbody>')
        stableford_parts.append('</table>')

        return ''.join(gross_parts), ''.join(stableford_parts)

    except Exception as e:
        error_msg = f"<div class='scorecard-container-mobile'><p>Error: {str(e)}</p></div>"
        return error_msg, error_msg


def generate_round_comparison_table_mobile(teg_num: int, round_num: int) -> tuple:
    """Generate HTML tables for multi-player round comparison (MOBILE).

    Returns tuple of (gross_table_html, stableford_table_html).

    Args:
        teg_num: Tournament number
        round_num: Round number

    Returns:
        Tuple of (gross_scores_html, stableford_points_html)
    """
    try:
        # Load data
        round_data = get_scorecard_data(teg_num, round_num)

        if round_data.empty:
            error_msg = f"<div class='scorecard-container-mobile'><p>Error: No data found for TEG {teg_num} Round {round_num}.</p></div>"
            return error_msg, error_msg

        players = round_data['Pl'].unique()

        # Sort players by total score
        player_totals = []
        for player in players:
            player_data = round_data[round_data['Pl'] == player]
            total_score = int(player_data['Sc'].sum())
            player_name = player_data['Player'].iloc[0]
            player_totals.append((total_score, player, player_name))

        player_totals.sort(key=lambda x: x[0])
        sorted_players = [(player, name) for _, player, name in player_totals]

        # Build Gross Scores table
        gross_parts = []
        gross_parts.append('<table class="scorecard-table-mobile layout-mobile-multi-player">')

        gross_parts.append('<thead>')
        gross_parts.append('<tr>')
        gross_parts.append('<th class="hole-label-mobile">Hole</th>')
        for _, player_name in sorted_players:
            gross_parts.append(f'<th class="player-header-mobile">{player_name[:3]}</th>')
        gross_parts.append('</tr>')
        gross_parts.append('</thead>')

        gross_parts.append('<tbody>')

        for hole in range(1, 19):
            gross_parts.append('<tr>')
            gross_parts.append(f'<td class="hole-label-mobile">{hole}</td>')

            for player_code, _ in sorted_players:
                player_data = round_data[round_data['Pl'] == player_code]
                hole_data = player_data[player_data['Hole'] == hole]

                if not hole_data.empty:
                    vs_par = int(hole_data.iloc[0]['GrossVP'])
                    score = int(hole_data.iloc[0]['Sc'])
                    gross_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
                else:
                    gross_parts.append('<td></td>')

            gross_parts.append('</tr>')

            if hole == 9:
                gross_parts.append('<tr>')
                gross_parts.append('<td class="hole-label-mobile">OUT</td>')
                for player_code, _ in sorted_players:
                    player_data = round_data[round_data['Pl'] == player_code]
                    front_total = int(player_data[player_data['Hole'] <= 9]['Sc'].sum())
                    gross_parts.append(f'<td class="totals-mobile">{front_total}</td>')
                gross_parts.append('</tr>')

        gross_parts.append('<tr>')
        gross_parts.append('<td class="hole-label-mobile">TOTAL</td>')
        for player_code, _ in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            total_score = int(player_data['Sc'].sum())
            gross_parts.append(f'<td class="totals-mobile">{total_score}</td>')
        gross_parts.append('</tr>')

        gross_parts.append('</tbody>')
        gross_parts.append('</table>')

        # Build Stableford Points table
        stableford_parts = []
        stableford_parts.append('<table class="scorecard-table-mobile layout-mobile-multi-player">')

        stableford_parts.append('<thead>')
        stableford_parts.append('<tr>')
        stableford_parts.append('<th class="hole-label-mobile">Hole</th>')
        for _, player_name in sorted_players:
            stableford_parts.append(f'<th class="player-header-mobile">{player_name[:3]}</th>')
        stableford_parts.append('</tr>')
        stableford_parts.append('</thead>')

        stableford_parts.append('<tbody>')

        for hole in range(1, 19):
            stableford_parts.append('<tr>')
            stableford_parts.append(f'<td class="hole-label-mobile">{hole}</td>')

            for player_code, _ in sorted_players:
                player_data = round_data[round_data['Pl'] == player_code]
                hole_data = player_data[player_data['Hole'] == hole]

                if not hole_data.empty:
                    stableford = int(hole_data.iloc[0]['Stableford'])
                    stableford_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
                else:
                    stableford_parts.append('<td></td>')

            stableford_parts.append('</tr>')

            if hole == 9:
                stableford_parts.append('<tr>')
                stableford_parts.append('<td class="hole-label-mobile">OUT</td>')
                for player_code, _ in sorted_players:
                    player_data = round_data[round_data['Pl'] == player_code]
                    front_total = int(player_data[player_data['Hole'] <= 9]['Stableford'].sum())
                    stableford_parts.append(f'<td class="totals-mobile">{front_total}</td>')
                stableford_parts.append('</tr>')

        stableford_parts.append('<tr>')
        stableford_parts.append('<td class="hole-label-mobile">TOTAL</td>')
        for player_code, _ in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            total_stableford = int(player_data['Stableford'].sum())
            stableford_parts.append(f'<td class="totals-mobile">{total_stableford}</td>')
        stableford_parts.append('</tr>')

        stableford_parts.append('</tbody>')
        stableford_parts.append('</table>')

        return ''.join(gross_parts), ''.join(stableford_parts)

    except Exception as e:
        error_msg = f"<div class='scorecard-container-mobile'><p>Error: {str(e)}</p></div>"
        return error_msg, error_msg
