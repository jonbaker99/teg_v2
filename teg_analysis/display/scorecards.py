"""Scorecard HTML generation utilities.

UI-agnostic functions for generating scorecard HTML tables.
No streamlit imports. All functions return HTML strings.
"""

import pandas as pd
from datetime import datetime
from typing import Optional


def _format_date(date_str: str) -> str:
    """Parse DD/MM/YYYY and return '17 March 2026' style."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        return str(date_str)


def _build_hole_header_row(label_class: str, label_text: str) -> str:
    """Build the hole-number header row."""
    parts = [f'<tr><th class="{label_class} hole-header">{label_text}</th>']
    for hole in range(1, 10):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals">IN</th>')
    parts.append('<th class="hole-header totals">TOTAL</th>')
    parts.append('</tr>')
    return ''.join(parts)


def _build_par_row(df_par: pd.DataFrame, label_class: str) -> str:
    """Build the PAR row using par data from one player/round."""
    front_par = int(df_par[df_par['Hole'] <= 9]['PAR'].sum())
    back_par = int(df_par[df_par['Hole'] > 9]['PAR'].sum())
    total_par = int(df_par['PAR'].sum())

    parts = [f'<tr><th class="{label_class} par-header">PAR</th>']
    for hole in range(1, 10):
        val = int(df_par[df_par['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{val}</th>')
    parts.append(f'<th class="totals front-back-divider par-header">{front_par}</th>')
    for hole in range(10, 19):
        val = int(df_par[df_par['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{val}</th>')
    parts.append(f'<th class="totals par-header">{back_par}</th>')
    parts.append(f'<th class="totals par-header">{total_par}</th>')
    parts.append('</tr>')
    return ''.join(parts)


def build_single_round_combined_table(df: pd.DataFrame) -> str:
    """Build a single combined scorecard for one player, single round.

    One table with the hole/PAR header followed by a gross ``Score`` row and a
    ``Stableford`` row — mirrors the Streamlit single-round card.

    Args:
        df: 18-row DataFrame for one player/round with Hole, PAR, Sc, GrossVP,
            Stableford cols.

    Returns:
        HTML string for the combined scorecard table.
    """
    df = df.sort_values('Hole')
    front_9 = df[df['Hole'] <= 9]
    back_9 = df[df['Hole'] > 9]
    front_sc, back_sc, total_sc = int(front_9['Sc'].sum()), int(back_9['Sc'].sum()), int(df['Sc'].sum())
    front_sf, back_sf, total_sf = int(front_9['Stableford'].sum()), int(back_9['Stableford'].sum()), int(df['Stableford'].sum())

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('label-column', 'Hole'))
    parts.append(_build_par_row(df, 'label-column'))
    parts.append('</thead><tbody>')

    # Gross score row
    parts.append('<tr><td class="label-column">Score</td>')
    for hole in range(1, 10):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-vs-par="{int(row["GrossVP"])}"><span>{int(row["Sc"])}</span></td>')
    parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
    for hole in range(10, 19):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-vs-par="{int(row["GrossVP"])}"><span>{int(row["Sc"])}</span></td>')
    parts.append(f'<td class="totals">{back_sc}</td>')
    parts.append(f'<td class="totals">{total_sc}</td>')
    parts.append('</tr>')

    # Stableford row
    parts.append('<tr><td class="label-column">Stableford</td>')
    for hole in range(1, 10):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-stableford="{int(row["Stableford"])}"><span>{int(row["Stableford"])}</span></td>')
    parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
    for hole in range(10, 19):
        row = df[df['Hole'] == hole].iloc[0]
        parts.append(f'<td class="score-cell" data-stableford="{int(row["Stableford"])}"><span>{int(row["Stableford"])}</span></td>')
    parts.append(f'<td class="totals">{back_sf}</td>')
    parts.append(f'<td class="totals">{total_sf}</td>')
    parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_tournament_gross_table(player_data: pd.DataFrame) -> str:
    """Build gross scores table for one player across all tournament rounds.

    Args:
        player_data: DataFrame for one player with Round, Hole, Sc, GrossVP, PAR cols.

    Returns:
        HTML string for the gross scores table (one row per round).
    """
    rounds = sorted(player_data['Round'].unique())
    par_data = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('round-label', 'Round'))
    parts.append(_build_par_row(par_data, 'round-label'))
    parts.append('</thead><tbody>')

    for round_num in rounds:
        rd = player_data[player_data['Round'] == round_num].sort_values('Hole')
        front_sc = int(rd[rd['Hole'] <= 9]['Sc'].sum())
        back_sc = int(rd[rd['Hole'] > 9]['Sc'].sum())
        total_sc = int(rd['Sc'].sum())

        parts.append(f'<tr><td class="round-label">Round {round_num}</td>')
        for hole in range(1, 10):
            row = rd[rd['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
        for hole in range(10, 19):
            row = rd[rd['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        parts.append(f'<td class="totals">{back_sc}</td>')
        parts.append(f'<td class="totals">{total_sc}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_tournament_stableford_table(player_data: pd.DataFrame) -> str:
    """Build stableford points table for one player across all tournament rounds.

    Args:
        player_data: DataFrame for one player with Round, Hole, Stableford, PAR cols.

    Returns:
        HTML string for the stableford points table (one row per round).
    """
    rounds = sorted(player_data['Round'].unique())
    par_data = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('round-label', 'Round'))
    parts.append(_build_par_row(par_data, 'round-label'))
    parts.append('</thead><tbody>')

    for round_num in rounds:
        rd = player_data[player_data['Round'] == round_num].sort_values('Hole')
        front_sf = int(rd[rd['Hole'] <= 9]['Stableford'].sum())
        back_sf = int(rd[rd['Hole'] > 9]['Stableford'].sum())
        total_sf = int(rd['Stableford'].sum())

        parts.append(f'<tr><td class="round-label">Round {round_num}</td>')
        for hole in range(1, 10):
            row = rd[rd['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span>{sf}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
        for hole in range(10, 19):
            row = rd[rd['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span>{sf}</span></td>')
        parts.append(f'<td class="totals">{back_sf}</td>')
        parts.append(f'<td class="totals">{total_sf}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def _get_sorted_players(round_data: pd.DataFrame):
    """Return list of (player_code, player_name) sorted by total gross score asc."""
    player_totals = []
    for player in round_data['Pl'].unique():
        pdata = round_data[round_data['Pl'] == player]
        total_score = int(pdata['Sc'].sum())
        player_name = pdata['Player'].iloc[0]
        player_totals.append((total_score, player, player_name))
    player_totals.sort(key=lambda x: x[0])
    return [(p, name) for _, p, name in player_totals]


def build_round_comparison_gross_table(round_data: pd.DataFrame) -> str:
    """Build gross scores table comparing all players in one round.

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player,
                    Hole, PAR, Sc, GrossVP cols.

    Returns:
        HTML string for the gross scores table (one row per player).
    """
    sorted_players = _get_sorted_players(round_data)
    first_player_data = round_data[round_data['Pl'] == round_data['Pl'].iloc[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('player-label', 'Player'))
    parts.append(_build_par_row(first_player_data, 'player-label'))
    parts.append('</thead><tbody>')

    for player_code, player_name in sorted_players:
        pdata = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_sc = int(pdata[pdata['Hole'] <= 9]['Sc'].sum())
        back_sc = int(pdata[pdata['Hole'] > 9]['Sc'].sum())
        total_sc = int(pdata['Sc'].sum())

        parts.append(f'<tr><td class="player-label">{player_name}</td>')
        for hole in range(1, 10):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sc}</td>')
        for hole in range(10, 19):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            vs_par = int(row['GrossVP'])
            score = int(row['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        parts.append(f'<td class="totals">{back_sc}</td>')
        parts.append(f'<td class="totals">{total_sc}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def build_round_comparison_stableford_table(round_data: pd.DataFrame) -> str:
    """Build stableford points table comparing all players in one round.

    Args:
        round_data: DataFrame for all players in a round, with Pl, Player,
                    Hole, PAR, Stableford cols.

    Returns:
        HTML string for the stableford points table (one row per player).
    """
    sorted_players = _get_sorted_players(round_data)
    first_player_data = round_data[round_data['Pl'] == round_data['Pl'].iloc[0]].sort_values('Hole')

    parts = ['<table class="scorecard-table"><thead>']
    parts.append(_build_hole_header_row('player-label', 'Player'))
    parts.append(_build_par_row(first_player_data, 'player-label'))
    parts.append('</thead><tbody>')

    for player_code, player_name in sorted_players:
        pdata = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_sf = int(pdata[pdata['Hole'] <= 9]['Stableford'].sum())
        back_sf = int(pdata[pdata['Hole'] > 9]['Stableford'].sum())
        total_sf = int(pdata['Stableford'].sum())

        parts.append(f'<tr><td class="player-label">{player_name}</td>')
        for hole in range(1, 10):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span>{sf}</span></td>')
        parts.append(f'<td class="totals front-back-divider">{front_sf}</td>')
        for hole in range(10, 19):
            row = pdata[pdata['Hole'] == hole].iloc[0]
            sf = int(row['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{sf}"><span>{sf}</span></td>')
        parts.append(f'<td class="totals">{back_sf}</td>')
        parts.append(f'<td class="totals">{total_sf}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)
