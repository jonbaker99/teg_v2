"""Admin-triggered remote report generation — the clubhouse use case.

A live report as soon as scores are in, read on a phone without ever touching
a laptop. The pipeline itself, the status-file state machine and the
background task all live in `webapp/report_generation.py`; this module is
route plumbing only — auth, form handling, picking which partial to render.

Flow:
  GET  /admin/reports          -> the generate-report page (TEG/round pickers)
  GET  /admin/reports/panel    -> re-render the panel for a different TEG (HTMX)
  POST /admin/reports/generate -> claim + enqueue a background run (HTMX)
  GET  /admin/reports/status   -> poll target while a run is in flight (HTMX)
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from webapp import deps, report_generation
from webapp.admin_auth import is_authed

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _redirect(url: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url, status_code=303)


def _unauthed_fragment() -> HTMLResponse:
    return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)


def _teg_is_complete(teg: int) -> bool:
    """A TEG's tournament report can only be written once it's finished —
    there is no "in progress" in-progress-teg row for it."""
    in_progress_num, _ = deps.get_current_in_progress_teg_fast()
    return teg != in_progress_num


def _panel_ctx(request: Request, teg: int, round_num: int) -> dict:
    from teg_analysis.reporting import newspaper_edition

    tegs = deps.get_available_teg_numbers()
    if teg not in tegs:
        teg = deps.get_default_teg_num()
    rounds = deps.get_rounds_for_teg(teg)
    if round_num not in rounds:
        round_num = rounds[-1] if rounds else 0

    try:
        rounds_with_reports = set(newspaper_edition.available_rounds(teg))
    except Exception:  # noqa: BLE001
        rounds_with_reports = set()
    try:
        has_tournament_report = newspaper_edition.has_edition(teg)
    except Exception:  # noqa: BLE001
        has_tournament_report = False

    round_status = report_generation.read_status(teg, round_num) if round_num else None
    tournament_status = report_generation.read_status(teg, None)

    # On a fresh page load, only an already-in-flight run needs the live
    # polling container — a finished/errored one is shown as a static badge
    # next to its button instead (see the template). If a round happened to
    # be mid-run too, it wins arbitrarily; both keep their own status file
    # regardless, so nothing is lost, just not both shown live at once.
    active_status, active_kind, active_round = None, None, None
    if report_generation.is_active(tournament_status):
        active_status, active_kind, active_round = tournament_status, "tournament", None
    if report_generation.is_active(round_status):
        active_status, active_kind, active_round = round_status, "round", round_num

    return {
        "request": request,
        "tegs": tegs,
        "selected_teg": teg,
        "rounds": rounds,
        "selected_round": round_num,
        "teg_complete": _teg_is_complete(teg),
        "has_tournament_report": has_tournament_report,
        "rounds_with_reports": rounds_with_reports,
        "round_status": round_status,
        "tournament_status": tournament_status,
        "status": active_status,
        "kind": active_kind,
        "round": active_round,
        "teg": teg,
        "error_message": None,
    }


@router.get("/admin/reports")
def admin_reports_page(request: Request, teg: Optional[int] = None, round: int = 0):
    if not is_authed(request):
        return _redirect("/admin/login")

    ctx = _panel_ctx(request, teg or deps.get_default_teg_num(), round)
    ctx["active_page"] = None
    return templates.TemplateResponse("admin_reports.html", ctx)


@router.get("/admin/reports/panel", response_class=HTMLResponse)
def admin_reports_panel(request: Request, teg: int, round: int = 0):
    if not is_authed(request):
        return _unauthed_fragment()

    ctx = _panel_ctx(request, teg, round)
    return templates.TemplateResponse("partials/admin_report_panel.html", ctx)


@router.post("/admin/reports/generate", response_class=HTMLResponse)
def admin_reports_generate(request: Request, background_tasks: BackgroundTasks,
                           kind: str = Form(...), teg: int = Form(...), round: int = Form(0)):
    if not is_authed(request):
        return _unauthed_fragment()

    if kind not in ("round", "tournament"):
        return HTMLResponse('<p class="error">Unknown report kind.</p>', status_code=400)
    if teg not in deps.get_available_teg_numbers():
        return HTMLResponse('<p class="error">Unknown TEG.</p>', status_code=400)

    round_num = None if kind == "tournament" else round

    error_message = None
    if kind == "round" and round_num not in deps.get_rounds_for_teg(teg):
        error_message = f"TEG {teg} has no round {round_num}."
    elif kind == "tournament" and not _teg_is_complete(teg):
        error_message = f"TEG {teg} is still in progress — the tournament report needs the final round in first."

    if error_message is None:
        error_message = report_generation.claim(teg, round_num)

    if error_message is None:
        background_tasks.add_task(report_generation.generate_report, teg, round_num)

    status = report_generation.read_status(teg, round_num)
    return templates.TemplateResponse("partials/admin_report_status.html", {
        "request": request, "teg": teg, "round": round_num, "kind": kind,
        "status": status, "error_message": error_message,
    })


@router.get("/admin/reports/status", response_class=HTMLResponse)
def admin_reports_status(request: Request, teg: int, round: int = 0, kind: str = "round"):
    if not is_authed(request):
        return _unauthed_fragment()

    round_num = None if kind == "tournament" else round
    status = report_generation.read_status(teg, round_num)
    return templates.TemplateResponse("partials/admin_report_status.html", {
        "request": request, "teg": teg, "round": round_num, "kind": kind,
        "status": status, "error_message": None,
    })
