"""TEG roster + handicap setup: confirming who's playing before a TEG starts.

Not every player plays every TEG. This page lets an admin confirm the roster
and each player's handicap ahead of time, prefilled from handicaps.csv (if
already saved for this TEG) or the calculated draft (if not) — the same two
sources the read-only Handicaps page already uses.

Flow:
  GET  /admin/teg-setup                       -> the next TEG's roster form (default target)
  GET  /admin/teg-setup/{teg_num}             -> the roster form for any TEG
  POST /admin/teg-setup/{teg_num}/save        -> save, re-render the result
  POST /admin/teg-setup/{teg_num}/add-player  -> register a brand-new player, reload the form
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from webapp.admin_auth import is_authed
from webapp import deps

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _redirect(url: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url, status_code=303)


@router.get("/admin/teg-setup")
def admin_teg_setup_default(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.teg_setup import get_next_teg

    try:
        next_teg = get_next_teg()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Could not determine next TEG: {e}", exc_info=True)
        next_teg = 1

    return _redirect(f"/admin/teg-setup/{next_teg}")


@router.get("/admin/teg-setup/{teg_num}")
def admin_teg_setup_form(request: Request, teg_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.teg_setup import get_teg_roster_form

    ctx = {
        "request": request, "active_page": None, "teg_num": teg_num,
        "added": request.query_params.get("added"),
        "add_error": request.query_params.get("add_error"),
    }
    try:
        ctx["form"] = get_teg_roster_form(teg_num)
    except Exception as e:  # noqa: BLE001
        logger.error(f"TEG setup form load failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load setup form: {e}"

    return templates.TemplateResponse("admin_teg_setup.html", ctx)


@router.post("/admin/teg-setup/{teg_num}/add-player")
def admin_teg_setup_add_player(request: Request, teg_num: int,
                               new_code: str = Form(""), new_name: str = Form("")):
    """Register a brand-new player (never played before), then reload the form.

    A plain form POST -> redirect (not HTMX): the new player has to appear as
    a fresh row in the roster table, so a whole-page re-render is the point.
    Errors round-trip via the query string for the same reason.
    """
    if not is_authed(request):
        return _redirect("/admin/login")

    from urllib.parse import quote
    from teg_analysis.core.players import add_player, PlayerError

    try:
        result = add_player(new_code, new_name)
        deps.clear_all_data_caches()
    except PlayerError as e:
        return _redirect(f"/admin/teg-setup/{teg_num}?add_error={quote(str(e))}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Add player failed: {e}", exc_info=True)
        return _redirect(f"/admin/teg-setup/{teg_num}?add_error={quote(f'Could not add player: {e}')}")

    return _redirect(f"/admin/teg-setup/{teg_num}?added={quote(result['code'])}")


@router.post("/admin/teg-setup/{teg_num}/save", response_class=HTMLResponse)
async def admin_teg_setup_save(request: Request, teg_num: int):
    # async because it reads dynamic-keyed form fields (playing__{code} /
    # handicap__{code}); the blocking save (a GitHub commit) is offloaded below.
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.teg_setup import get_roster_players, save_teg_roster

    form = await request.form()
    ctx = {"request": request, "teg_num": teg_num}

    players = []
    for code in get_roster_players():
        playing = form.get(f"playing__{code}") == "on"
        handicap = form.get(f"handicap__{code}", "").strip()
        if playing and not handicap:
            ctx["error"] = f"{code} is marked as playing but has no handicap — enter one or untick them."
            return templates.TemplateResponse("partials/admin_teg_setup_result.html", ctx)
        players.append({"code": code, "playing": playing, "handicap": handicap or None})

    try:
        ctx["result"] = await run_in_threadpool(save_teg_roster, teg_num, players)
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"TEG setup save failed: {e}", exc_info=True)
        ctx["error"] = f"Save failed: {e}"

    return templates.TemplateResponse("partials/admin_teg_setup_result.html", ctx)
