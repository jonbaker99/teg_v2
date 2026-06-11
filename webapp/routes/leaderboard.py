"""Leaderboard routes.

The Latest Leaderboard mirrors the Full Results page (`/results`) for the latest
TEG, reusing its context builder so the two stay in sync. Differences: there is
no Report tab, and the latest TEG may be in progress (fewer rounds) — the data
reflects this automatically because it flows through the same round-level
pipeline as /results.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.deps import get_default_teg_num, get_available_teg_numbers
from webapp.routes.history import _results_context

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Tab labels match /results (minus Report).
LEADERBOARD_TABS = [
    ("net", "TEG Trophy"),
    ("gross", "Green Jacket"),
    ("scorecards", "Scorecards"),
]


def _lb_context(teg_num: int, tab: str, chart_variant: str) -> dict:
    """Same content as /results, plus a link to the full Scorecard page on the
    scorecards tab (the leaderboard shows scorecards inline as well)."""
    ctx = _results_context(teg_num, tab, chart_variant)
    if tab == "scorecards" and "error" not in ctx:
        ctx["scorecards_full_link"] = f"/scorecard?teg={teg_num}"
    return ctx


@router.get("/leaderboard")
async def leaderboard_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _lb_context(teg_num, "net", "standard")
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "active_page": "leaderboard",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "leaderboard_tabs": LEADERBOARD_TABS,
        "active_lb_tab": "net",
        "active_chart_variant": "standard",
        **ctx,
    })


@router.get("/leaderboard/table")
async def leaderboard_table(
    request: Request,
    teg: int = Query(...),
    tab: str = Query("net"),
    chart_variant: str = Query("standard"),
):
    ctx = _lb_context(teg, tab, chart_variant)
    return templates.TemplateResponse("partials/leaderboard_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_lb_tab": tab,
        "leaderboard_tabs": LEADERBOARD_TABS,
        "active_chart_variant": chart_variant,
        **ctx,
    })
