"""Leaderboard routes.

The Latest Leaderboard mirrors the Full Results page (`/results`) for the latest
TEG, reusing its context builder so the two stay in sync. The latest TEG may be
in progress (fewer rounds) — the data reflects this automatically because it
flows through the same round-level pipeline as /results. The Report tab is a
link to /teg-reports (not an HTMX swap) and is hidden unless the selected TEG
has a newspaper edition; since `available_tegs()` only considers TEGs in
completed_tegs.csv, an in-progress TEG never shows one.
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.reporting.newspaper_edition import available_tegs
from webapp.deps import get_default_teg_num, get_available_teg_numbers
from webapp.routes.history import RESULTS_CHART_TYPES, _results_context
from webapp.routes.scorecard import parse_scorecard_round

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _lb_context(teg_num: int, tab: str, chart_variant: str,
                scorecard_type: str = "one_round_all_players",
                scorecard_round: int | None = None,
                scorecard_player: str | None = None) -> dict:
    """Same content as /results, plus a link to the full Scorecard page on the
    scorecards tab (the leaderboard shows scorecards inline as well)."""
    ctx = _results_context(teg_num, tab, chart_variant, scorecard_type=scorecard_type,
                           scorecard_round=scorecard_round, scorecard_player=scorecard_player)
    if tab == "scorecards" and "error" not in ctx:
        ctx["scorecards_full_link"] = "/scorecard?" + urlencode({
            "teg": teg_num, "type": ctx["selected_type"],
            "round": ctx["selected_round"], "player": ctx["selected_player"],
        })
    return ctx


@router.get("/leaderboard")
def leaderboard_page(
    request: Request,
    teg: Optional[int] = Query(None),
    tab: str = Query("net"),
    chart_variant: str = Query("adjusted"),
    type: str = Query("one_round_all_players"),
    round: str | None = Query(None),
    player: str | None = Query(None),
):
    teg_numbers = get_available_teg_numbers()
    teg_num = teg if teg in teg_numbers else get_default_teg_num()
    tab = tab if tab in {"net", "gross", "scorecards"} else "net"
    chart_variant = (chart_variant if chart_variant in {value for value, _label in RESULTS_CHART_TYPES}
                     else "adjusted")
    selected_round = parse_scorecard_round(round)
    ctx = _lb_context(teg_num, tab, chart_variant, type, selected_round, player)
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "active_page": "leaderboard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "active_lb_tab": tab,
        "active_chart_variant": chart_variant,
        "sc_saved_type": ctx.get("selected_type", type),
        "sc_saved_round": ctx.get("selected_round", selected_round),
        "sc_saved_player": ctx.get("selected_player", player),
        "report_tegs": list(available_tegs()),
        **ctx,
    })


@router.get("/leaderboard/table")
def leaderboard_table(
    request: Request,
    teg: int = Query(...),
    tab: str = Query("net"),
    chart_variant: str = Query("adjusted"),
    type: str = Query("one_round_all_players"),
    round: str | None = Query(None),
    player: str | None = Query(None),
):
    ctx = _lb_context(teg, tab, chart_variant, type, parse_scorecard_round(round), player)
    return templates.TemplateResponse("partials/leaderboard_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_lb_tab": tab,
        "active_chart_variant": chart_variant,
        **ctx,
    })
