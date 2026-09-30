"""Admin side of live round entry: start, review/resolve conflicts, finalize.

The player-facing side (the entry page itself, plus its poll/write API) lives
in webapp/routes/live_round.py and is deliberately NOT behind this cookie
auth -- a live round's shareable link is its own access control (Phase 3.4
design in DATA_STORAGE_INGESTION_PLAN.md). Only lifecycle actions (starting,
resolving, finalizing, cancelling a round) are admin-only.

Flow:
  GET  /admin/live-round                        -> list every live round + status
  POST /admin/live-round/public-link             -> switch the public "Enter scores" banner on/off
  POST /admin/live-round/start                   -> start one (HTMX, from a set-up round)
  GET  /admin/live-round/{token}/review           -> conflicts + finalize/cancel controls
  POST /admin/live-round/{token}/resolve          -> pick a value for one conflicted cell
  POST /admin/live-round/{token}/random-fill      -> test only: fill empty cells with random scores (off on production)
  POST /admin/live-round/{token}/finalize         -> start the background finalise (webapp/finalize_jobs.py)
  GET  /admin/live-round/{token}/finalize-status  -> polled: progress, or HX-Redirect when done
  POST /admin/live-round/{token}/cancel           -> abandon without touching all-scores

Finalize takes ~40 s, so the POST only claims a job and returns a self-polling
progress partial; the job runs as a BackgroundTask and its state lives in a
status file (survives a reload; the admin can leave the page). When the poll
sees "done" it answers with an empty 200 + HX-Redirect to the review page
(?finalized=1), as cancel does (?cancelled=1); the page then renders read-only
with a status card at the top. Errors render into #finalize-result instead.
"""

import logging
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from webapp.admin_auth import is_authed
from webapp import deps, finalize_jobs
from webapp.report_generation import fmt_hhmm

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
templates.env.globals["fmt_hhmm"] = fmt_hhmm
templates.env.globals["finalize_step_rows"] = finalize_jobs.step_rows
templates.env.globals["finalize_current_step"] = finalize_jobs.current_step


def _entry_url(request: Request, token: str) -> str:
    """Absolute player score-entry URL for a live round, on whatever host served this request.

    Behind Railway's proxy the app sees plain http, so honour X-Forwarded-Proto
    -- otherwise the copied link would start http:// on an https site.
    """
    url = str(request.url_for("live_round_page", token=token))
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    if proto in ("http", "https") and not url.startswith(proto + "://"):
        url = proto + url[url.index("://"):]
    return url


def _random_fill_enabled() -> bool:
    """Test-only random fill is off on production. Railway sets RAILWAY_ENVIRONMENT_NAME
    (RAILWAY_ENVIRONMENT is its older alias); locally neither is set, so it's on."""
    name = os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_ENVIRONMENT") or ""
    return name.strip().lower() != "production"


def _fmt_started(iso: str) -> str:
    """"29 Sep 2026, 19:32" (UTC) from a registry CreatedAt; the page's script
    swaps it for the viewer's local time. Unparseable values pass through."""
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%-d %b %Y, %H:%M")


def _redirect(url: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url, status_code=303)


@router.get("/admin/live-round")
def admin_live_round_list(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import list_live_rounds
    from teg_analysis.analysis.round_setup import get_rounds_status

    ctx = {"request": request, "active_page": None, "saved": request.query_params.get("saved")}
    try:
        from teg_analysis.analysis.live_round import get_public_entry_enabled
        ctx["public_link_on"] = get_public_entry_enabled()
        ctx["live_rounds"] = list_live_rounds()
        ctx["started"] = {r["Token"]: _fmt_started(r["CreatedAt"]) for r in ctx["live_rounds"]}
        # Entry link per active round, so it's never lost after "Go live".
        ctx["entry_urls"] = {
            r["Token"]: _entry_url(request, r["Token"])
            for r in ctx["live_rounds"] if r["Status"] == "active"
        }
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
        ctx["public_link_on"] = False
        ctx["entry_urls"] = {}
        ctx["started"] = {}
        ctx["startable_rounds"] = []

    return templates.TemplateResponse("admin_live_round.html", ctx)


@router.post("/admin/live-round/public-link")
def admin_live_round_public_link(request: Request, enabled: str = Form("")):
    """Plain form POST: show or hide the public site's "Enter scores" banner."""
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import set_public_entry_enabled

    on = enabled == "on"
    try:
        set_public_entry_enabled(on)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Public link switch failed: {e}", exc_info=True)
        return _redirect("/admin/live-round?saved=error")
    deps.clear_public_live_rounds_cache()
    return _redirect(f"/admin/live-round?saved={'on' if on else 'off'}")


@router.post("/admin/live-round/start", response_class=HTMLResponse)
def admin_live_round_start(request: Request, teg_num: str = Form(""), round_num: str = Form("")):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import (
        start_live_round, RoundParsNotConfirmedError, LiveRoundAlreadyActiveError,
    )

    ctx = {"request": request}
    try:
        row = start_live_round(int(teg_num), int(round_num))
        deps.clear_public_live_rounds_cache()
        ctx["result"] = row
        ctx["link"] = _entry_url(request, row["Token"])
    except (RoundParsNotConfirmedError, LiveRoundAlreadyActiveError) as e:
        ctx["error"] = str(e)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round start failed: {e}", exc_info=True)
        ctx["error"] = f"Could not start live round: {e}"

    return templates.TemplateResponse("partials/admin_live_round_start_result.html", ctx)


@router.get("/admin/live-round/{token}/review")
def admin_live_round_review(request: Request, token: str):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import get_live_round_context, get_scores_since

    ctx = {
        "request": request, "token": token,
        "saved": request.query_params.get("saved"),
        "error": request.query_params.get("error"),
        "finalized": request.query_params.get("finalized"),
        "cancelled": request.query_params.get("cancelled"),
        "cache_errors": [
            c for c in (request.query_params.get("cache_errors") or "").split(",") if c
        ],
        "random_fill_enabled": _random_fill_enabled(),
    }
    try:
        live_ctx = get_live_round_context(token)
        if live_ctx is None:
            ctx["error"] = f"No live round found for token {token}."
        else:
            ctx["live"] = live_ctx
            ctx["read_only"] = live_ctx["status"] != "active"
            if live_ctx["status"] == "active":
                ctx["entry_url"] = _entry_url(request, token)
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
            # Check if TEG roster is confirmed (needed for accurate net/Stableford scoring)
            from teg_analysis.analysis.teg_setup import get_teg_roster_form
            roster = get_teg_roster_form(int(live_ctx["teg_num"]))
            ctx["roster_confirmed"] = roster["source"] == "confirmed"
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round review failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load review: {e}"

    # A finalise started earlier (or by another phone): resume its progress,
    # or show why it failed. Only while the round is still active.
    if ctx.get("live") and not ctx["read_only"]:
        job = finalize_jobs.read_status(token)
        if finalize_jobs.is_active(job):
            ctx["finalize_job"] = job
        else:
            ctx["finalize_error"] = finalize_jobs.error_message(job)
            ctx["finalize_status"] = job

    # The finalised card: the latest job's checklist (cache failures and their
    # errors), what happens next, and whether a report can be generated yet.
    if ctx.get("live") and ctx["live"]["status"] == "finalized":
        job = finalize_jobs.read_status(token)
        ctx["job"] = job
        ctx["job_steps"] = bool(job and job.get("steps"))
        ctx["job_done"] = bool(job and job.get("state") == "done")
        ctx["job_committed"] = bool(job and job.get("committed"))
        ctx["report_block"] = finalize_jobs.report_block(
            int(ctx["live"]["teg_num"]), int(ctx["live"]["round_num"]))

    return templates.TemplateResponse("admin_live_round_review.html", ctx)


@router.post("/admin/live-round/{token}/edit")
async def admin_live_round_edit(request: Request, token: str):
    """Bulk admin edit of the staged scorecard from the review grid.

    A plain form POST (not HTMX): posts every cell's value, writes only the
    ones that changed (via apply_admin_edits, which is authoritative and clears
    any conflict), then redirects back to the review page so the whole grid
    re-renders from the saved state.

    async because it reads a dynamic-keyed form (score-{hole}-{player}); the
    blocking write (apply_admin_edits) is offloaded to the threadpool below.
    """
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.live_round import (
        apply_admin_edits, LiveRoundNotFoundError, LiveRoundInactiveError,
        InvalidScoreCellError, MAX_SCORE,
    )

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
            if value < 1 or value > MAX_SCORE:
                continue  # ignore out-of-range typos rather than write them
        cells.append({"hole": hole, "player": player, "value": value})

    try:
        result = await run_in_threadpool(apply_admin_edits, token, cells, "Admin")
        written = result["written"]
    except LiveRoundNotFoundError:
        return _redirect(f"/admin/live-round/{token}/review")
    except InvalidScoreCellError as e:
        logger.warning(f"Live round admin edit rejected invalid cells: {e.errors}")
        return _redirect(f"/admin/live-round/{token}/review?error={quote(str(e))}")
    except LiveRoundInactiveError as e:
        return _redirect(f"/admin/live-round/{token}/review?error={quote(str(e))}")

    return _redirect(f"/admin/live-round/{token}/review?saved={written}")


@router.post("/admin/live-round/{token}/random-fill")
def admin_live_round_random_fill(request: Request, token: str):
    """Test-only: fill every empty cell with a random plausible score, then back to review."""
    if not is_authed(request):
        return _redirect("/admin/login")
    if not _random_fill_enabled():
        return HTMLResponse("Random fill is disabled on production.", status_code=403)

    from teg_analysis.analysis.live_round import (
        fill_random_scores, LiveRoundNotFoundError, LiveRoundInactiveError, InvalidScoreCellError,
    )

    try:
        written = fill_random_scores(token)["written"]
    except (LiveRoundNotFoundError, LiveRoundInactiveError, InvalidScoreCellError) as e:
        return _redirect(f"/admin/live-round/{token}/review?error={quote(str(e))}")
    return _redirect(f"/admin/live-round/{token}/review?saved={written}")


@router.post("/admin/live-round/{token}/resolve", response_class=HTMLResponse)
def admin_live_round_resolve(request: Request, token: str, hole: str = Form(""),
                             player: str = Form(""), chosen_value: str = Form("")):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import resolve_conflict, LiveRoundNotFoundError

    ctx = {"request": request, "token": token}
    try:
        hole_num, chosen = int(hole), int(chosen_value)
        resolve_conflict(token, hole=hole_num, player=player, chosen_value=chosen, resolved_by="Admin")
        ctx["resolved"] = {"hole": hole_num, "player": player, "value": chosen}
    except LiveRoundNotFoundError:
        ctx["error"] = "Live round not found."
    except Exception as e:  # noqa: BLE001
        logger.error(f"Conflict resolve failed: {e}", exc_info=True)
        ctx["error"] = f"Could not resolve conflict: {e}"

    return templates.TemplateResponse("partials/admin_live_round_resolve_result.html", ctx)


@router.post("/admin/live-round/{token}/finalize", response_class=HTMLResponse)
def admin_live_round_finalize(request: Request, token: str, background_tasks: BackgroundTasks):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    ctx = {"request": request, "token": token}
    active = finalize_jobs.claim(token)
    if active and active.get("state") == "done":
        return HTMLResponse("", headers={"HX-Redirect": f"/admin/live-round/{token}/review?finalized=1"})
    if active:
        ctx["status"] = active
        ctx["note"] = f"Already finalising (started {fmt_hhmm(active.get('started_at'))} UTC)."
    else:
        background_tasks.add_task(finalize_jobs.run_finalize, token)
        ctx["status"] = finalize_jobs.read_status(token)
    return templates.TemplateResponse("partials/admin_live_round_finalize_progress.html", ctx)


@router.get("/admin/live-round/{token}/finalize-status", response_class=HTMLResponse)
def admin_live_round_finalize_status(request: Request, token: str):
    """Polled by the progress partial: keep polling, redirect on done, else show the error."""
    if not is_authed(request):
        # htmx ignores a 4xx swap, so a 401 would leave the poll running forever.
        return HTMLResponse("", headers={"HX-Redirect": "/admin/login"})

    ctx = {"request": request, "token": token}
    status = finalize_jobs.read_status(token)
    if finalize_jobs.is_active(status):
        ctx["status"] = status
        return templates.TemplateResponse("partials/admin_live_round_finalize_progress.html", ctx)
    if status and status.get("state") == "done":
        url = f"/admin/live-round/{token}/review?finalized=1"
        steps = status.get("cache_errors") or []
        if steps:
            url += "&cache_errors=" + quote(",".join(steps), safe="")
        return HTMLResponse("", headers={"HX-Redirect": url})
    ctx["status"] = status
    ctx["error"] = finalize_jobs.error_message(status) or "No finalise run found for this round."
    return templates.TemplateResponse("partials/admin_live_round_finalize_result.html", ctx)


@router.post("/admin/live-round/{token}/cancel", response_class=HTMLResponse)
def admin_live_round_cancel(request: Request, token: str):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.live_round import cancel_live_round, LiveRoundNotFoundError

    ctx = {"request": request, "token": token}
    try:
        cancel_live_round(token)
        deps.clear_public_live_rounds_cache()
        return HTMLResponse("", headers={"HX-Redirect": f"/admin/live-round/{token}/review?cancelled=1"})
    except LiveRoundNotFoundError:
        ctx["error"] = "Live round not found."
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round cancel failed: {e}", exc_info=True)
        ctx["error"] = f"Could not cancel: {e}"

    return templates.TemplateResponse("partials/admin_live_round_cancel_result.html", ctx)
