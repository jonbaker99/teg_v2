"""Player-facing live round entry: the page itself, plus its poll/write API.

Deliberately NOT behind admin cookie auth -- the token in the URL is the
access control (a live round's shareable link), matching the "trust the
small group" model already used elsewhere in this app. Only the lifecycle
actions (start/resolve/finalize/cancel) in admin_live_round.py require the
admin cookie.

This renders a standalone page (not webapp/templates/base.html's desktop
site chrome) -- it's a focused, phone-first tool for mid-round use, styled
like the webapp/mobile_mockups/round_entry_grid.html reference it's ported
from, not a page in the site's nav.

Flow:
  GET  /live-round/{token}                 -> the entry page
  GET  /api/live-round/{token}/scores       -> poll for changes since a seq
  POST /api/live-round/{token}/scores       -> write N cells (a tap, or a whole voice batch)
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class ScoreCell(BaseModel):
    hole: int
    player: str
    value: int | None = None


class ScoreWriteRequest(BaseModel):
    device_id: str
    device_name: str
    cells: list[ScoreCell]


@router.get("/live-round/{token}", name="live_round_page")
async def live_round_page(request: Request, token: str):
    from teg_analysis.analysis.live_round import get_live_round_context

    ctx = {"request": request, "token": token}
    try:
        live_ctx = get_live_round_context(token)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round page load failed: {e}", exc_info=True)
        live_ctx = None
        ctx["error"] = "Something went wrong loading this round."

    if live_ctx is None:
        ctx.setdefault("error", "This link doesn't match a live round. Check the link, or ask whoever started the round.")
    elif not live_ctx["players"]:
        ctx["error"] = "No players are registered for this TEG yet — ask the admin to set up the roster on TEG setup first."
    else:
        ctx["live"] = live_ctx

    return templates.TemplateResponse("live_round_entry.html", ctx)


@router.get("/live-round/{token}/leaderboard", name="live_round_leaderboard_page")
async def live_round_leaderboard_page(request: Request, token: str):
    from teg_analysis.analysis.live_round import get_live_leaderboard

    ctx = {"request": request, "token": token}
    try:
        board = get_live_leaderboard(token)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live leaderboard load failed: {e}", exc_info=True)
        board = None
        ctx["error"] = "Something went wrong loading the leaderboard."

    if board is None:
        ctx.setdefault("error", "This link doesn't match a live round. Check the link, or ask whoever started the round.")
    else:
        ctx["board"] = board

    return templates.TemplateResponse("live_round_leaderboard.html", ctx)


@router.get("/api/live-round/{token}/leaderboard")
async def api_live_leaderboard(token: str):
    from teg_analysis.analysis.live_round import get_live_leaderboard

    board = get_live_leaderboard(token)
    if board is None:
        raise HTTPException(status_code=404, detail="Live round not found")
    return board


@router.get("/api/live-round/{token}/scores")
async def api_poll_scores(token: str, since: int = 0):
    from teg_analysis.analysis.live_round import get_scores_since, LiveRoundNotFoundError

    try:
        return get_scores_since(token, since_seq=since)
    except LiveRoundNotFoundError:
        raise HTTPException(status_code=404, detail="Live round not found")


@router.post("/api/live-round/{token}/scores")
async def api_write_scores(token: str, body: ScoreWriteRequest):
    from teg_analysis.analysis.live_round import (
        apply_score_writes, LiveRoundNotFoundError, LiveRoundInactiveError,
    )

    if not body.cells:
        raise HTTPException(status_code=400, detail="No cells to write")

    try:
        return apply_score_writes(
            token, body.device_id, body.device_name,
            [c.model_dump() for c in body.cells],
        )
    except LiveRoundNotFoundError:
        raise HTTPException(status_code=404, detail="Live round not found")
    except LiveRoundInactiveError as e:
        raise HTTPException(status_code=409, detail=str(e))
