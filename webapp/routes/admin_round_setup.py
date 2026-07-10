"""Pre-round setup: confirming a round's Par/SI before anyone plays it.

A player entering scores (Phase 3+ mobile round entry, not built yet) sees
Par/SI on the entry screen like it's printed on a scorecard, but never edits
it — that would put course-setup responsibility on whoever happens to be
scoring. This page is where an admin confirms the Par/SI for a specific
TEG+Round ahead of time, prefilled from course_pars.csv (the most recently
played round at that course) and editable before saving to round_pars.csv,
which round entry will read from.

Flow:
  GET  /admin/round-setup                         -> list every TEG+Round + status
  GET  /admin/round-setup/{teg}/{round}            -> the 18-hole form for one round
  POST /admin/round-setup/{teg}/{round}/save       -> save, re-render the form
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
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


@router.get("/admin/round-setup")
def admin_round_setup_list(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.round_setup import get_rounds_status

    ctx = {"request": request, "active_page": None}
    try:
        ctx["rounds"] = get_rounds_status()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Round setup list failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load rounds: {e}"
        ctx["rounds"] = []

    return templates.TemplateResponse("admin_round_setup.html", ctx)


@router.get("/admin/round-setup/{teg_num}/{round_num}")
def admin_round_setup_form(request: Request, teg_num: int, round_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.round_setup import get_round_setup_form

    ctx = {"request": request, "active_page": None, "teg_num": teg_num, "round_num": round_num}
    try:
        ctx["form"] = get_round_setup_form(teg_num, round_num)
    except ValueError as e:
        ctx["error"] = str(e)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Round setup form load failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load setup form: {e}"

    return templates.TemplateResponse("admin_round_setup_form.html", ctx)


@router.post("/admin/round-setup/{teg_num}/{round_num}/save", response_class=HTMLResponse)
async def admin_round_setup_save(request: Request, teg_num: int, round_num: int):
    # async because it reads dynamic-keyed form fields (par__{h} / si__{h});
    # the blocking save (a GitHub commit) is offloaded to the threadpool below.
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.round_setup import save_round_setup

    form = await request.form()
    ctx = {"request": request, "teg_num": teg_num, "round_num": round_num}

    holes = []
    for h in range(1, 19):
        par = form.get(f"par__{h}", "").strip()
        si = form.get(f"si__{h}", "").strip()
        if not par or not si:
            ctx["error"] = f"Hole {h} is missing a Par or SI value — every hole must be filled in."
            return templates.TemplateResponse("partials/admin_round_setup_result.html", ctx)
        holes.append({"hole": h, "par": par, "si": si})

    try:
        ctx["result"] = await run_in_threadpool(save_round_setup, teg_num, round_num, holes)
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Round setup save failed: {e}", exc_info=True)
        ctx["error"] = f"Save failed: {e}"

    return templates.TemplateResponse("partials/admin_round_setup_result.html", ctx)
