"""Leaderboard routes.

The Latest Leaderboard mirrors the Full Results page (`/results`) for the latest
TEG, reusing its context builder so the two stay in sync. The latest TEG may be
in progress (fewer rounds) — the data reflects this automatically because it
flows through the same round-level pipeline as /results.

Tabs: net / gross (leaderboard), scorecards, and reports. The Reports tab is
always shown: it lists each round of the TEG with its round report's lead
headline (linking to that report), or "Pending" (TEG in progress) / "No report"
(TEG complete) when a round has none. A completed TEG with a tournament edition
also shows the tournament headline on top. The hero "View tournament report"
link to /teg-reports is separate (a plain link, not an HTMX swap) and hidden
unless the selected TEG has an edition; `available_tegs()` only considers TEGs
in completed_tegs.csv, so an in-progress TEG never shows one.
"""

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.io.file_operations import read_file
from teg_analysis.reporting.newspaper_edition import available_tegs, get_edition_summary
from webapp.deps import get_default_teg_num, get_available_teg_numbers
from webapp.routes.history import RESULTS_CHART_TYPES, _results_context, _teg_is_complete
from webapp.routes.scorecard import parse_scorecard_round

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

LB_TABS = ("net", "gross", "scorecards", "reports")


def _round_rows(teg_num: int) -> list[dict]:
    """Rounds of a TEG as [{"round", "course"}], from round_info.csv.

    If round_info is unreadable or has no rows for the TEG, falls back to the
    round count from the venue context (the same source `available_rounds`
    probes), so unreported rounds still show as pending."""
    try:
        df = read_file("data/round_info.csv")
        df = df.assign(TEGNum=pd.to_numeric(df["TEGNum"], errors="coerce"),
                       Round=pd.to_numeric(df["Round"], errors="coerce"))
        df = (df[df["TEGNum"] == teg_num].dropna(subset=["Round"])
              .drop_duplicates("Round").sort_values("Round"))
        rows = []
        for _, r in df.iterrows():
            course = r.get("Course")
            course = str(course).strip() if isinstance(course, str) else ""
            rows.append({"round": int(r["Round"]), "course": course or None})
        if rows:
            return rows
    except Exception:          # noqa: BLE001 - degrade to the venue fallback
        logger.warning("round_info read failed for TEG %s", teg_num, exc_info=True)
    try:
        from teg_analysis.reporting.venue import build_venue_context
        total = len(build_venue_context(teg_num).get("rounds", []))
    except Exception:          # noqa: BLE001 - no round_info for this TEG at all
        return []
    return [{"round": r, "course": None} for r in range(1, total + 1)]


def _reports_context(teg_num: int) -> dict:
    """Context for the Reports tab: round report headlines for one TEG.

    A TEG with no rounds set up yet gets an empty list (an honest empty
    state), not an error: a Retry could never fix it."""
    from webapp.routes.latest import _teg_context_header  # avoid import cycle
    complete = _teg_is_complete(teg_num)
    tournament = (get_edition_summary(teg_num)
                  if complete and teg_num in available_tegs() else None)
    return {
        "reports_view": True,
        "teg_complete": complete,
        "context_header": _teg_context_header(teg_num),
        "tournament_summary": tournament,
        "rounds": [{**r, "summary": get_edition_summary(teg_num, r["round"])}
                   for r in _round_rows(teg_num)],
        "pending_label": "No report" if complete else "Pending",
    }


def _lb_context(teg_num: int, tab: str, chart_variant: str,
                scorecard_type: str = "one_round_all_players",
                scorecard_round: int | None = None,
                scorecard_player: str | None = None) -> dict:
    """Same content as /results, plus a link to the full Scorecard page on the
    scorecards tab (the leaderboard shows scorecards inline as well)."""
    if tab == "reports":
        return _reports_context(teg_num)
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
    tab = tab if tab in LB_TABS else "net"
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
    tab = tab if tab in LB_TABS else "net"
    ctx = _lb_context(teg, tab, chart_variant, type, parse_scorecard_round(round), player)
    return templates.TemplateResponse("partials/leaderboard_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_lb_tab": tab,
        "active_chart_variant": chart_variant,
        **ctx,
    })
