"""Scorecard routes — hole-by-hole scorecard views."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.core.metadata import get_scorecard_data, get_teg_metadata
from teg_analysis.constants import PLAYER_DICT
from teg_analysis.display.scorecards import (
    build_single_round_combined_table,
    build_single_round_combined_portrait,
    build_tournament_gross_table,
    build_tournament_stableford_table,
    build_tournament_gross_portrait,
    build_tournament_stableford_portrait,
    build_round_comparison_gross_table,
    build_round_comparison_stableford_table,
    build_round_comparison_gross_portrait,
    build_round_comparison_stableford_portrait,
)
from webapp.deps import (
    get_default_teg_num,
    get_available_teg_numbers,
    get_rounds_for_teg,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# View type constants
TYPE_ONE_ROUND_ONE_PLAYER = "one_round_one_player"
TYPE_ONE_PLAYER_ALL_ROUNDS = "one_player_all_rounds"
TYPE_ONE_ROUND_ALL_PLAYERS = "one_round_all_players"

ALL_TYPES = [
    (TYPE_ONE_ROUND_ONE_PLAYER, "1 Round / 1 Player"),
    (TYPE_ONE_PLAYER_ALL_ROUNDS, "1 Player / All Rounds"),
    (TYPE_ONE_ROUND_ALL_PLAYERS, "1 Round / All Players"),
]

# Player list: sorted by display name for the selector
_PLAYER_LIST = sorted(PLAYER_DICT.items(), key=lambda x: x[1])


def _format_date(date_str: str) -> str:
    """Parse DD/MM/YYYY and return '17 March 2026' style."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        return str(date_str)


def _default_player_code() -> str:
    """Return the first player code (alphabetically by name)."""
    return _PLAYER_LIST[0][0]


def _scorecard_context_one_round_one_player(teg_num: int, round_num: int, player_code: str) -> dict:
    """Build context for single player, single round view."""
    try:
        df = get_scorecard_data(teg_num, round_num, player_code)
        if df.empty or len(df) != 18:
            count = len(df)
            return {"error": f"Expected 18 holes, found {count} for TEG {teg_num} Round {round_num}, player {player_code}."}

        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course', '')
        date_str = metadata.get('Date', '')
        formatted_date = _format_date(date_str)
        subheader_parts = [p for p in [course, formatted_date] if p]
        subheader = ' | '.join(subheader_parts) if subheader_parts else None

        player_name = df['Player'].iloc[0]
        title = f"{player_name} | TEG {teg_num}, Round {round_num}"

        # Single combined card: one gross "Score" row + one "Stableford" row.
        # Landscape (holes as columns) + portrait (holes as rows, mobile).
        combined_table = build_single_round_combined_table(df)
        combined_portrait = build_single_round_combined_portrait(df)

        return {
            "title": title,
            "subheader": subheader,
            "combined_table": combined_table,
            "combined_portrait": combined_portrait,
        }
    except Exception as e:
        return {"error": str(e)}


def _scorecard_context_one_player_all_rounds(teg_num: int, player_code: str) -> dict:
    """Build context for single player, all rounds view."""
    try:
        player_data = get_scorecard_data(teg_num, player_code=player_code)
        if player_data.empty:
            return {"error": f"No data found for player {player_code} in TEG {teg_num}."}

        metadata = get_teg_metadata(teg_num)
        area = metadata.get('Area', '')
        year = metadata.get('Year', '')
        subheader_parts = [str(p) for p in [area, year] if p]
        subheader = ' | '.join(subheader_parts) if subheader_parts else None

        player_name = player_data['Player'].iloc[0]
        title = f"{player_name} | TEG {teg_num}"

        gross_table = build_tournament_gross_table(player_data)
        stableford_table = build_tournament_stableford_table(player_data)
        gross_portrait = build_tournament_gross_portrait(player_data)
        stableford_portrait = build_tournament_stableford_portrait(player_data)

        return {
            "title": title,
            "subheader": subheader,
            "gross_table": gross_table,
            "stableford_table": stableford_table,
            "gross_portrait": gross_portrait,
            "stableford_portrait": stableford_portrait,
        }
    except Exception as e:
        return {"error": str(e)}


def _scorecard_context_one_round_all_players(teg_num: int, round_num: int) -> dict:
    """Build context for all players, single round view."""
    try:
        round_data = get_scorecard_data(teg_num, round_num)
        if round_data.empty:
            return {"error": f"No data found for TEG {teg_num}, Round {round_num}."}

        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course', '')
        date_str = metadata.get('Date', '')
        formatted_date = _format_date(date_str)
        subheader_parts = [p for p in [course, formatted_date] if p]
        subheader = ' | '.join(subheader_parts) if subheader_parts else None

        title = f"TEG {teg_num}, Round {round_num}"

        gross_table = build_round_comparison_gross_table(round_data)
        stableford_table = build_round_comparison_stableford_table(round_data)
        gross_portrait = build_round_comparison_gross_portrait(round_data)
        stableford_portrait = build_round_comparison_stableford_portrait(round_data)

        return {
            "title": title,
            "subheader": subheader,
            "gross_table": gross_table,
            "stableford_table": stableford_table,
            "gross_portrait": gross_portrait,
            "stableford_portrait": stableford_portrait,
        }
    except Exception as e:
        return {"error": str(e)}


def _build_scorecard_context(
    view_type: str,
    teg_num: int,
    round_num: int,
    player_code: str,
) -> dict:
    """Dispatch to the appropriate context builder based on view type."""
    if view_type == TYPE_ONE_ROUND_ONE_PLAYER:
        return _scorecard_context_one_round_one_player(teg_num, round_num, player_code)
    elif view_type == TYPE_ONE_PLAYER_ALL_ROUNDS:
        return _scorecard_context_one_player_all_rounds(teg_num, player_code)
    else:  # TYPE_ONE_ROUND_ALL_PLAYERS (default)
        return _scorecard_context_one_round_all_players(teg_num, round_num)


@router.get("/scorecard")
async def scorecard_page(
    request: Request,
    teg: int = None,
    round: int = None,
    player: str = None,
    type: str = TYPE_ONE_ROUND_ALL_PLAYERS,
):
    teg_num = teg or get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    rounds = get_rounds_for_teg(teg_num)
    round_num = round if round is not None else (rounds[-1] if rounds else 1)
    player_code = player or _default_player_code()

    ctx = _build_scorecard_context(type, teg_num, round_num, player_code)

    return templates.TemplateResponse("scorecard.html", {
        "request": request,
        "active_page": "scorecard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "selected_round": round_num,
        "selected_player": player_code,
        "selected_type": type,
        "player_list": _PLAYER_LIST,
        "all_types": ALL_TYPES,
        "rounds": rounds,
        **ctx,
    })


@router.get("/scorecard/content")
async def scorecard_content(
    request: Request,
    teg: int = Query(...),
    round: int = Query(None),
    player: str = Query(None),
    type: str = Query(TYPE_ONE_ROUND_ALL_PLAYERS),
):
    rounds = get_rounds_for_teg(teg)
    round_num = round if round is not None else (rounds[-1] if rounds else 1)
    player_code = player or _default_player_code()

    ctx = _build_scorecard_context(type, teg, round_num, player_code)

    return templates.TemplateResponse("partials/scorecard_content.html", {
        "request": request,
        "selected_teg": teg,
        "selected_round": round_num,
        "selected_player": player_code,
        "selected_type": type,
        "rounds": rounds,
        **ctx,
    })
