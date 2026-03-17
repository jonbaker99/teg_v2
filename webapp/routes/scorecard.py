"""Scorecard routes — hole-by-hole round comparison view."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.core.metadata import get_scorecard_data, get_teg_metadata
from webapp.deps import (
    get_default_teg_num,
    get_available_teg_numbers,
    get_rounds_for_teg,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _format_date(date_str: str) -> str:
    """Parse DD/MM/YYYY and return '17 March 2026' style."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        return str(date_str)


def _build_gross_table_html(round_data, first_player_data, sorted_players,
                            front_par_total, back_par_total, total_par) -> str:
    """Build HTML for the gross scores table."""
    parts = []
    parts.append('<table class="scorecard-table">')

    # Header: hole numbers
    parts.append('<thead><tr>')
    parts.append('<th class="player-label hole-header">Player</th>')
    for hole in range(1, 10):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals">IN</th>')
    parts.append('<th class="hole-header totals">TOTAL</th>')
    parts.append('</tr>')

    # PAR row
    parts.append('<tr>')
    parts.append('<th class="player-label par-header">PAR</th>')
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{par_val}</th>')
    parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{par_val}</th>')
    parts.append(f'<th class="totals par-header">{back_par_total}</th>')
    parts.append(f'<th class="totals par-header">{total_par}</th>')
    parts.append('</tr></thead>')

    # Body — one row per player
    parts.append('<tbody>')
    for player_code, player_name in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_total = int(player_data[player_data['Hole'] <= 9]['Sc'].sum())
        back_total = int(player_data[player_data['Hole'] > 9]['Sc'].sum())
        total_score = int(player_data['Sc'].sum())

        parts.append('<tr>')
        parts.append(f'<td class="player-label">{player_name}</td>')

        for hole in range(1, 10):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

        parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

        for hole in range(10, 19):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

        parts.append(f'<td class="totals">{back_total}</td>')
        parts.append(f'<td class="totals">{total_score}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def _build_stableford_table_html(round_data, first_player_data, sorted_players,
                                  front_par_total, back_par_total, total_par) -> str:
    """Build HTML for the stableford points table."""
    parts = []
    parts.append('<table class="scorecard-table">')

    # Header: hole numbers
    parts.append('<thead><tr>')
    parts.append('<th class="player-label hole-header">Player</th>')
    for hole in range(1, 10):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        parts.append(f'<th class="hole-header">{hole}</th>')
    parts.append('<th class="hole-header totals">IN</th>')
    parts.append('<th class="hole-header totals">TOTAL</th>')
    parts.append('</tr>')

    # PAR row
    parts.append('<tr>')
    parts.append('<th class="player-label par-header">PAR</th>')
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{par_val}</th>')
    parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        parts.append(f'<th class="par-header">{par_val}</th>')
    parts.append(f'<th class="totals par-header">{back_par_total}</th>')
    parts.append(f'<th class="totals par-header">{total_par}</th>')
    parts.append('</tr></thead>')

    # Body — one row per player
    parts.append('<tbody>')
    for player_code, player_name in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        front_total = int(player_data[player_data['Hole'] <= 9]['Stableford'].sum())
        back_total = int(player_data[player_data['Hole'] > 9]['Stableford'].sum())
        total_stableford = int(player_data['Stableford'].sum())

        parts.append('<tr>')
        parts.append(f'<td class="player-label">{player_name}</td>')

        for hole in range(1, 10):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

        parts.append(f'<td class="totals front-back-divider">{front_total}</td>')

        for hole in range(10, 19):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')

        parts.append(f'<td class="totals">{back_total}</td>')
        parts.append(f'<td class="totals">{total_stableford}</td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    return ''.join(parts)


def _scorecard_context(teg_num: int, round_num: int) -> dict:
    """Build template context for a given TEG and round."""
    try:
        round_data = get_scorecard_data(teg_num, round_num)

        if round_data.empty:
            return {"error": f"No data found for TEG {teg_num}, Round {round_num}."}

        # Metadata
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course', '')
        date_str = metadata.get('Date', '')
        formatted_date = _format_date(date_str)

        subheader_parts = [p for p in [course, formatted_date] if p]
        subheader = ' | '.join(subheader_parts) if subheader_parts else None

        # Sort players by total gross score ascending
        players = round_data['Pl'].unique()
        player_totals = []
        for player in players:
            pdata = round_data[round_data['Pl'] == player]
            total_score = int(pdata['Sc'].sum())
            player_name = pdata['Player'].iloc[0]
            player_totals.append((total_score, player, player_name))
        player_totals.sort(key=lambda x: x[0])
        sorted_players = [(p, name) for _, p, name in player_totals]

        # PAR totals from first player's data
        first_player_data = round_data[round_data['Pl'] == players[0]].sort_values('Hole')
        front_par_total = int(first_player_data[first_player_data['Hole'] <= 9]['PAR'].sum())
        back_par_total = int(first_player_data[first_player_data['Hole'] > 9]['PAR'].sum())
        total_par = int(first_player_data['PAR'].sum())

        gross_table = _build_gross_table_html(
            round_data, first_player_data, sorted_players,
            front_par_total, back_par_total, total_par
        )
        stableford_table = _build_stableford_table_html(
            round_data, first_player_data, sorted_players,
            front_par_total, back_par_total, total_par
        )

        rounds = get_rounds_for_teg(teg_num)

        return {
            "subheader": subheader,
            "gross_table": gross_table,
            "stableford_table": stableford_table,
            "rounds": rounds,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/scorecard")
async def scorecard_page(request: Request, teg: int = None, round: int = 1):
    teg_num = teg or get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _scorecard_context(teg_num, round)
    return templates.TemplateResponse("scorecard.html", {
        "request": request,
        "active_page": "scorecard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "selected_round": round,
        **ctx,
    })


@router.get("/scorecard/content")
async def scorecard_content(request: Request, teg: int = Query(...), round: int = Query(1)):
    ctx = _scorecard_context(teg, round)
    return templates.TemplateResponse("partials/scorecard_content.html", {
        "request": request,
        "selected_teg": teg,
        "selected_round": round,
        **ctx,
    })
