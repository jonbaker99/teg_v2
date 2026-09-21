"""Contents route — current-TEG home page with the full site map below.

State-led home (I3/I5): shows the in-progress TEG, the latest completed TEG,
or an honest no-data message, chosen by `webapp.deps.get_tournament_state()`.
The complete public site map (`webapp.nav.NAV_SECTIONS`, unchanged) always
renders beneath it, so every destination stays reachable regardless of state.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.nav import NAV_SECTIONS
from webapp.deps import get_tournament_state, get_contents_state1_leaders

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/contents")
def contents_page(request: Request):
    return templates.TemplateResponse("contents.html", {
        "request": request,
        "active_page": "contents",
        "sections": NAV_SECTIONS,
        "state": get_tournament_state(),
    })


@router.get("/contents/leaders")
def contents_state1_leaders(request: Request, teg: int = Query(...)):
    # HTMX fallback for a cold State 1 render (I4 R10): the main page renders
    # the headline/context/actions immediately from the two status CSVs, and
    # this partial fills in the leader rows once cached_round_data() has
    # loaded, instead of blocking the initial response on a cold parquet
    # load. Reuses the same partial as the inline (warm-cache) render.
    leaders = get_contents_state1_leaders(teg)
    return templates.TemplateResponse("partials/_contents_state1_leaders.html", {
        "request": request,
        "leaders": leaders,
    })
