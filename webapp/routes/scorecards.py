"""Scorecards section routes: /bestball."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.bestball import format_team_scores_for_display
from webapp.deps import (
    cached_load_all_data,
    bestball_worstball_totals,
    get_available_teg_numbers,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table") -> str:
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"
    rows = [f"<table class='{table_class}'><thead><tr>"]
    for col in df.columns:
        rows.append(f"<th>{col}</th>")
    rows.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in df.columns:
            rows.append(f"<td>{row[col]}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _bestball_context(mode: str = "bestball", teg: int = 0, sort_best: bool = True, n: int = 3) -> dict:
    try:
        all_data = cached_load_all_data()
        # Per-round totals from the maintained cache (live fallback inside).
        bb_scores, wb_scores = bestball_worstball_totals(all_data)

        if mode == "worstball":
            scores = wb_scores
            format_label = "Worstball"
        else:
            scores = bb_scores
            format_label = "Bestball"

        # A round's team-format total is independent of TEG filtering, so we can
        # filter the cached per-round result rather than recomputing per TEG.
        if teg > 0:
            scores = scores[scores['TEGNum'] == teg]

        # Dynamic heading: sort_best=True means ascending GrossVP (lowest/best first)
        # bestball + sort_best=True  → Best Bestball
        # bestball + sort_best=False → Worst Bestball
        # worstball + sort_best=True  → Best Worstball
        # worstball + sort_best=False → Worst Worstball
        best_or_worst = "Best" if sort_best else "Worst"
        title = f"{best_or_worst} {format_label}"

        display = format_team_scores_for_display(scores, sort_by_best=sort_best)
        if n > 0:
            display = display.head(n)
        table_html = _df_to_html(display)
        return {"title": title, "table_html": table_html}
    except Exception as e:
        return {"error": str(e)}


@router.get("/bestball")
async def bestball_page(request: Request, teg: int = 0, sort_best: bool = True, n: int = 3):
    ctx = _bestball_context("bestball", teg, sort_best, n)
    teg_numbers = get_available_teg_numbers()
    return templates.TemplateResponse("bestball.html", {
        "request": request,
        "active_page": "scorecards",
        "active_mode": "bestball",
        "teg_numbers": teg_numbers,
        "selected_teg": teg,
        "sort_best": sort_best,
        "n_rows": n,
        **ctx,
    })


@router.get("/bestball/content")
async def bestball_content(request: Request, mode: str = "bestball", teg: int = 0, sort_best: bool = True, n: int = 3):
    ctx = _bestball_context(mode, teg, sort_best, n)
    return templates.TemplateResponse("partials/bestball_content.html", {
        "request": request,
        "active_mode": mode,
        **ctx,
    })
