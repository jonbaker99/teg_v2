"""'New round' setup wizard: one guided flow for setting up a TEG/round.

Setting up a brand-new TEG's first round touches four separate admin pages in
a specific order (metadata -> roster -> Par/SI -> go live); a new round in an
existing TEG touches three of them. This wizard is a thin orchestration layer
that walks an admin through only the incomplete steps and hands over the
shareable link at the end. It reuses the already-tested save functions in
``round_wizard`` / ``teg_setup`` / ``round_setup`` / ``live_round`` -- the
standalone pages stay reachable in the sub-nav for edits and edge cases.

The wizard holds no session state: every step saves immediately, and which
step is "current" is recomputed from the data on each visit
(``round_wizard.get_wizard_status``), so a half-finished setup resumes just by
revisiting the URL.

Flow:
  GET  /admin/new-round                          -> landing: pick TEG+Round / resume
  GET  /admin/new-round/{teg}/{round}            -> the wizard at its current step
  POST /admin/new-round/{teg}/{round}/metadata   -> save round_info row, advance
  POST /admin/new-round/{teg}/{round}/roster     -> save handicaps row, advance
  POST /admin/new-round/{teg}/{round}/parsi      -> save round_pars, advance
  POST /admin/new-round/{teg}/{round}/golive     -> start live round, show link
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.templating import Jinja2Templates

from webapp.admin_auth import is_authed
from webapp import deps

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _redirect(url: str):
    return RedirectResponse(url, status_code=303)


def _render_wizard(request: Request, teg_num: int, round_num: int,
                   step: str | None = None, error: str | None = None,
                   notice: str | None = None):
    """Build and render the wizard at a given (or the current) step.

    Shared by the wizard GET and by every POST handler's error path so a
    failed save re-renders the same step with its message instead of losing it
    to a redirect.
    """
    from teg_analysis.analysis.round_wizard import (
        get_wizard_status, get_round_metadata_form, STEP_KEYS,
    )

    if step is not None and step not in STEP_KEYS:
        step = None

    ctx = {
        "request": request, "active_page": None,
        "teg_num": teg_num, "round_num": round_num,
        "error": error, "notice": notice,
    }
    try:
        status = get_wizard_status(teg_num, round_num)
        ctx["status"] = status

        if status["already_played"]:
            ctx["active_step"] = "played"
            return templates.TemplateResponse("admin_new_round_wizard.html", ctx)

        active = step or status["current"]
        ctx["active_step"] = active

        if active == "metadata":
            ctx["meta_form"] = get_round_metadata_form(teg_num, round_num)
        elif active == "roster":
            from teg_analysis.analysis.teg_setup import get_teg_roster_form
            ctx["roster_form"] = get_teg_roster_form(teg_num)
        elif active == "parsi":
            from teg_analysis.analysis.round_setup import get_round_setup_form
            try:
                ctx["parsi_form"] = get_round_setup_form(teg_num, round_num)
            except ValueError as e:
                # Metadata not saved yet -- send them back to step 1.
                ctx["active_step"] = "metadata"
                ctx["meta_form"] = get_round_metadata_form(teg_num, round_num)
                ctx["error"] = ctx["error"] or str(e)
        elif active == "golive" and status["live"]:
            ctx["review_link"] = f"/admin/live-round/{status['live']['token']}/review"
            if status["live"]["status"] == "active":
                ctx["live_link"] = str(
                    request.url_for("live_round_page", token=status["live"]["token"])
                )
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round wizard render failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load the setup wizard: {e}"

    return templates.TemplateResponse("admin_new_round_wizard.html", ctx)


@router.get("/admin/new-round")
async def admin_new_round_landing(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.round_wizard import suggest_next_target
    from teg_analysis.analysis.round_setup import get_rounds_status

    ctx = {"request": request, "active_page": None}
    try:
        ctx["suggested"] = suggest_next_target()
        # Rounds with metadata but no scores yet -- the resume/quick-pick list.
        ctx["pending"] = get_rounds_status()
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round landing failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load: {e}"
        ctx["suggested"] = {"teg_num": 1, "round_num": 1}
        ctx["pending"] = []

    return templates.TemplateResponse("admin_new_round.html", ctx)


@router.get("/admin/new-round/{teg_num}/{round_num}")
async def admin_new_round_wizard(request: Request, teg_num: int, round_num: int, step: str | None = None):
    if not is_authed(request):
        return _redirect("/admin/login")
    return _render_wizard(request, teg_num, round_num, step=step)


@router.post("/admin/new-round/{teg_num}/{round_num}/metadata")
async def admin_new_round_metadata(request: Request, teg_num: int, round_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.round_wizard import save_round_metadata

    form = await request.form()
    course = (form.get("course") or "").strip()
    date = (form.get("date") or "").strip()
    try:
        save_round_metadata(teg_num, round_num, course, date)
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round metadata save failed: {e}", exc_info=True)
        return _render_wizard(request, teg_num, round_num, step="metadata", error=str(e))

    return _redirect(f"/admin/new-round/{teg_num}/{round_num}")


@router.post("/admin/new-round/{teg_num}/{round_num}/roster")
async def admin_new_round_roster(request: Request, teg_num: int, round_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.teg_setup import get_roster_players, save_teg_roster

    form = await request.form()
    players = []
    for code in get_roster_players():
        playing = form.get(f"playing__{code}") == "on"
        handicap = (form.get(f"handicap__{code}") or "").strip()
        if playing and not handicap:
            return _render_wizard(
                request, teg_num, round_num, step="roster",
                error=f"{code} is marked as playing but has no handicap — enter one or untick them.",
            )
        players.append({"code": code, "playing": playing, "handicap": handicap or None})

    try:
        save_teg_roster(teg_num, players)
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round roster save failed: {e}", exc_info=True)
        return _render_wizard(request, teg_num, round_num, step="roster", error=f"Save failed: {e}")

    return _redirect(f"/admin/new-round/{teg_num}/{round_num}")


@router.post("/admin/new-round/{teg_num}/{round_num}/parsi")
async def admin_new_round_parsi(request: Request, teg_num: int, round_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.round_setup import save_round_setup

    form = await request.form()
    holes = []
    for h in range(1, 19):
        par = (form.get(f"par__{h}") or "").strip()
        si = (form.get(f"si__{h}") or "").strip()
        if not par or not si:
            return _render_wizard(
                request, teg_num, round_num, step="parsi",
                error=f"Hole {h} is missing a Par or SI value — every hole must be filled in.",
            )
        holes.append({"hole": h, "par": par, "si": si})

    try:
        save_round_setup(teg_num, round_num, holes)
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round Par/SI save failed: {e}", exc_info=True)
        return _render_wizard(request, teg_num, round_num, step="parsi", error=f"Save failed: {e}")

    return _redirect(f"/admin/new-round/{teg_num}/{round_num}")


@router.post("/admin/new-round/{teg_num}/{round_num}/golive")
async def admin_new_round_golive(request: Request, teg_num: int, round_num: int):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import (
        start_live_round, RoundParsNotConfirmedError, LiveRoundAlreadyActiveError,
    )

    try:
        start_live_round(teg_num, round_num)
    except LiveRoundAlreadyActiveError:
        pass  # Already live -- fall through to show its link.
    except RoundParsNotConfirmedError as e:
        return _render_wizard(request, teg_num, round_num, step="parsi", error=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"New-round go-live failed: {e}", exc_info=True)
        return _render_wizard(request, teg_num, round_num, step="golive", error=f"Could not start live round: {e}")

    return _redirect(f"/admin/new-round/{teg_num}/{round_num}?step=golive")
