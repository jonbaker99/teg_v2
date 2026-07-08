"""Admin side of live round entry: start, review/resolve conflicts, finalize.

The player-facing side (the entry page itself, plus its poll/write API) lives
in webapp/routes/live_round.py and is deliberately NOT behind this cookie
auth -- a live round's shareable link is its own access control (Phase 3.4
design in DATA_STORAGE_INGESTION_PLAN.md). Only lifecycle actions (starting,
resolving, finalizing, cancelling a round) are admin-only.

Flow:
  GET  /admin/live-round                        -> list every live round + status
  POST /admin/live-round/start                   -> start one (HTMX, from a set-up round)
  GET  /admin/live-round/{token}/review           -> conflicts + finalize/cancel controls
  POST /admin/live-round/{token}/resolve          -> pick a value for one conflicted cell
  POST /admin/live-round/{token}/finalize         -> write to all-scores via execute_data_update
  POST /admin/live-round/{token}/cancel           -> abandon without touching all-scores
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from webapp.admin_auth import is_authed
from webapp import deps

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _redirect(url: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url, status_code=303)


@router.get("/admin/live-round")
async def admin_live_round_list(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import list_live_rounds
    from teg_analysis.analysis.round_setup import get_rounds_status

    ctx = {"request": request, "active_page": None}
    try:
        ctx["live_rounds"] = list_live_rounds()
        # Only rounds that are set up (confirmed Par/SI) and not already live
        # are worth offering to start -- mirrors round-setup's own scoping.
        already_started = {(r["TEGNum"], r["Round"]) for r in ctx["live_rounds"] if r["Status"] == "active"}
        ctx["startable_rounds"] = [
            r for r in get_rounds_status()
            if r["is_set_up"] and (r["teg_num"], r["round_num"]) not in already_started
        ]
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round list failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load live rounds: {e}"
        ctx["live_rounds"] = []
        ctx["startable_rounds"] = []

    return templates.TemplateResponse("admin_live_round.html", ctx)


@router.post("/admin/live-round/start", response_class=HTMLResponse)
async def admin_live_round_start(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import (
        start_live_round, RoundParsNotConfirmedError, LiveRoundAlreadyActiveError,
    )

    form = await request.form()
    ctx = {"request": request}
    try:
        teg_num, round_num = int(form.get("teg_num")), int(form.get("round_num"))
        row = start_live_round(teg_num, round_num)
        ctx["result"] = row
        ctx["link"] = str(request.url_for("live_round_page", token=row["Token"]))
    except (RoundParsNotConfirmedError, LiveRoundAlreadyActiveError) as e:
        ctx["error"] = str(e)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round start failed: {e}", exc_info=True)
        ctx["error"] = f"Could not start live round: {e}"

    return templates.TemplateResponse("partials/admin_live_round_start_result.html", ctx)


@router.get("/admin/live-round/{token}/review")
async def admin_live_round_review(request: Request, token: str):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import get_live_round_context, get_scores_since

    ctx = {"request": request, "token": token, "saved": request.query_params.get("saved")}
    try:
        live_ctx = get_live_round_context(token)
        if live_ctx is None:
            ctx["error"] = f"No live round found for token {token}."
        else:
            ctx["live"] = live_ctx
            polled = get_scores_since(token, since_seq=0)
            ctx["conflicts"] = [c for c in polled["cells"] if c["conflict"]]
            progress = {p: 0 for p in live_ctx["players"]}
            # Full grid keyed "hole-player" so the template can render an
            # editable scorecard with every entered score in place.
            grid = {}
            for c in polled["cells"]:
                if c["value"] is not None and c["player"] in progress:
                    progress[c["player"]] += 1
                grid[f"{c['hole']}-{c['player']}"] = {"value": c["value"], "conflict": c["conflict"]}
            ctx["progress"] = progress
            ctx["grid"] = grid
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round review failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load review: {e}"

    return templates.TemplateResponse("admin_live_round_review.html", ctx)


@router.post("/admin/live-round/{token}/edit")
async def admin_live_round_edit(request: Request, token: str):
    """Bulk admin edit of the staged scorecard from the review grid.

    A plain form POST (not HTMX): posts every cell's value, writes only the
    ones that changed (via apply_admin_edits, which is authoritative and clears
    any conflict), then redirects back to the review page so the whole grid
    re-renders from the saved state.
    """
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import apply_admin_edits, LiveRoundNotFoundError

    form = await request.form()
    cells = []
    for key, raw in form.items():
        if not key.startswith("score-"):
            continue
        try:
            _, hole_s, player = key.split("-", 2)
            hole = int(hole_s)
        except ValueError:
            continue
        raw = (raw or "").strip()
        if raw == "":
            value = None  # blank clears the cell
        else:
            try:
                value = int(raw)
            except ValueError:
                continue
            if value < 1 or value > 20:
                continue  # ignore out-of-range typos rather than write them
        cells.append({"hole": hole, "player": player, "value": value})

    try:
        result = apply_admin_edits(token, cells, resolved_by="Admin")
        written = result["written"]
    except LiveRoundNotFoundError:
        return _redirect(f"/admin/live-round/{token}/review")

    return _redirect(f"/admin/live-round/{token}/review?saved={written}")


@router.post("/admin/live-round/{token}/resolve", response_class=HTMLResponse)
async def admin_live_round_resolve(request: Request, token: str):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import resolve_conflict, LiveRoundNotFoundError

    form = await request.form()
    ctx = {"request": request, "token": token}
    try:
        hole, player = int(form.get("hole")), form.get("player")
        chosen_value = int(form.get("chosen_value"))
        resolve_conflict(token, hole=hole, player=player, chosen_value=chosen_value, resolved_by="Admin")
        ctx["resolved"] = {"hole": hole, "player": player, "value": chosen_value}
    except LiveRoundNotFoundError:
        ctx["error"] = "Live round not found."
    except Exception as e:  # noqa: BLE001
        logger.error(f"Conflict resolve failed: {e}", exc_info=True)
        ctx["error"] = f"Could not resolve conflict: {e}"

    return templates.TemplateResponse("partials/admin_live_round_resolve_result.html", ctx)


@router.post("/admin/live-round/{token}/finalize", response_class=HTMLResponse)
async def admin_live_round_finalize(request: Request, token: str):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import (
        finalize_live_round, ConflictsUnresolvedError, LiveRoundInactiveError, LiveRoundNotFoundError,
    )

    ctx = {"request": request, "token": token}
    try:
        ctx["result"] = finalize_live_round(token)
        deps.clear_all_data_caches()
    except ConflictsUnresolvedError as e:
        ctx["error"] = str(e)
    except (LiveRoundInactiveError, LiveRoundNotFoundError, ValueError) as e:
        ctx["error"] = str(e)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round finalize failed: {e}", exc_info=True)
        ctx["error"] = f"Finalize failed: {e}"

    return templates.TemplateResponse("partials/admin_live_round_finalize_result.html", ctx)


@router.post("/admin/live-round/{token}/cancel", response_class=HTMLResponse)
async def admin_live_round_cancel(request: Request, token: str):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import cancel_live_round, LiveRoundNotFoundError

    ctx = {"request": request, "token": token}
    try:
        ctx["result"] = cancel_live_round(token)
    except LiveRoundNotFoundError:
        ctx["error"] = "Live round not found."
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round cancel failed: {e}", exc_info=True)
        ctx["error"] = f"Could not cancel: {e}"

    return templates.TemplateResponse("partials/admin_live_round_cancel_result.html", ctx)
