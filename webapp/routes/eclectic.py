"""Eclectic routes: /eclectic."""

import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.eclectic import (
    calculate_eclectic_by_dimension,
    get_overall_top_eclectics,
    get_personal_best_eclectics,
    format_eclectic_records_table,
)
from teg_analysis.display.scorecards import build_eclectic_scorecard_table
from webapp.deps import cached_load_all_data
from webapp.tables import df_to_html as _df_to_html

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

ECLECTIC_TABS = [
    ("Player", "Player"),
    ("TEGNum", "TEG"),
    ("Course", "Course"),
    ("Teams", "Teams"),
    ("Combined", "Combined"),
]


def _get_eclectic_filter_options(all_data: pd.DataFrame) -> dict:
    """Return sorted lists of players, TEG numbers, and courses for filter dropdowns."""
    players = sorted(all_data['Player'].unique().tolist())
    tegs = sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    courses = sorted(all_data['Course'].unique().tolist())
    return {"players": players, "tegs": tegs, "courses": courses}


def _apply_eclectic_filters(
    all_data: pd.DataFrame,
    player: str = "",
    teg: int = 0,
    course: str = "",
) -> pd.DataFrame:
    """Filter all_data by the given player/teg/course selections."""
    filtered = all_data
    if player:
        filtered = filtered[filtered['Player'] == player]
    if teg > 0:
        filtered = filtered[filtered['TEGNum'] == teg]
    if course:
        filtered = filtered[filtered['Course'] == course]
    return filtered


def _eclectic_tab_context(
    dimension: str,
    player: str = "",
    teg: int = 0,
    course: str = "",
) -> dict:
    """Build context for an eclectic tab."""
    try:
        all_data = cached_load_all_data()
        filtered = _apply_eclectic_filters(all_data, player, teg, course)

        if filtered.empty:
            return {
                "table_html": "<p class='text-muted text-sm'>No data matches your selections.</p>",
                "total_rounds": 0,
            }

        eclectic_df, display_dim = calculate_eclectic_by_dimension(filtered, dimension)
        if eclectic_df.empty:
            return {
                "table_html": "<p class='text-muted text-sm'>No data available.</p>",
                "total_rounds": 0,
            }

        table_html = build_eclectic_scorecard_table(eclectic_df, display_dim)
        total_rounds = len(filtered.groupby(['Player', 'TEGNum', 'Round']))
        return {"table_html": table_html, "total_rounds": total_rounds}
    except Exception as e:
        logger.exception("_eclectic_tab_context failed")
        return {"error": str(e)}


@router.get("/eclectic")
def eclectic_page(
    request: Request,
    dimension: str = Query("Player"),
    player: str = Query(""),
    teg: int = Query(0),
    course: str = Query(""),
):
    all_data = cached_load_all_data()
    filter_opts = _get_eclectic_filter_options(all_data)
    dimension = dimension if dimension in {tab_id for tab_id, _label in ECLECTIC_TABS} else "Player"
    player = player if player in filter_opts["players"] else ""
    teg = teg if teg in filter_opts["tegs"] else 0
    course = course if course in filter_opts["courses"] else ""
    ctx = _eclectic_tab_context(dimension, player=player, teg=teg, course=course)
    return templates.TemplateResponse("eclectic.html", {
        "request": request,
        "active_page": "scorecards",
        "tabs": ECLECTIC_TABS,
        "active_tab": dimension,
        "selected_player": player,
        "selected_teg": teg,
        "selected_course": course,
        **filter_opts,
        **ctx,
    })


@router.get("/eclectic/tab")
def eclectic_tab(
    request: Request,
    dimension: str = Query("Player"),
    player: str = Query(""),
    teg: int = Query(0),
    course: str = Query(""),
):
    ctx = _eclectic_tab_context(dimension, player=player, teg=teg, course=course)
    return templates.TemplateResponse("partials/eclectic_tab.html", {
        "request": request,
        **ctx,
    })


# --- Eclectic Records ---------------------------------------------------------

ECLECTIC_RECORDS_TABS = [
    ("TEGNum", "TEGs"),
    ("Course", "Courses"),
]


def _eclectic_records_context(dimension: str) -> dict:
    """Build context for an eclectic-records tab (Top 3 + Personal Best tables)."""
    try:
        all_data = cached_load_all_data()
        dim_label = "TEG" if dimension == "TEGNum" else dimension

        top = get_overall_top_eclectics(all_data, dimension, top_n=3)
        pb = get_personal_best_eclectics(all_data, dimension)

        # Player column crowds TEG/Total/Rounds at 320-390px (see
        # .eclectic-records-page in mobile.css) -- shorten to Initial.SURNAME
        # there, matching mobile.css's now-narrower Player column width.
        sections = [
            {
                "title": f"Top 3 {dim_label} Eclectics",
                "table_html": _df_to_html(format_eclectic_records_table(top), shorten_players=True),
            },
            {
                "title": f"Personal Best {dim_label} Eclectics",
                "table_html": _df_to_html(format_eclectic_records_table(pb), shorten_players=True),
            },
        ]
        return {"sections": sections}
    except Exception as e:
        logger.exception("_eclectic_records_context failed")
        return {"error": str(e)}


@router.get("/eclectic-records")
def eclectic_records_page(request: Request, dimension: str = Query("TEGNum")):
    dimension = (dimension if dimension in {tab_id for tab_id, _label in ECLECTIC_RECORDS_TABS}
                 else "TEGNum")
    ctx = _eclectic_records_context(dimension)
    return templates.TemplateResponse("eclectic_records.html", {
        "request": request,
        "active_page": "scorecards",
        "tabs": ECLECTIC_RECORDS_TABS,
        "active_tab": dimension,
        **ctx,
    })


@router.get("/eclectic-records/tab")
def eclectic_records_tab(request: Request, dimension: str = Query("TEGNum")):
    ctx = _eclectic_records_context(dimension)
    return templates.TemplateResponse("partials/eclectic_records_tab.html", {
        "request": request,
        **ctx,
    })
