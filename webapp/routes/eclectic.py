"""Eclectic routes: /eclectic."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.eclectic import (
    calculate_eclectic_by_dimension,
    format_eclectic_table,
)
from webapp.deps import cached_load_all_data

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

ECLECTIC_TABS = [
    ("Player", "Player"),
    ("TEGNum", "TEG"),
    ("Course", "Course"),
    ("Teams", "Teams"),
    ("Combined", "Combined"),
]


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


def _eclectic_tab_context(dimension: str) -> dict:
    """Build context for an eclectic tab."""
    try:
        all_data = cached_load_all_data()
        eclectic_df, display_dim = calculate_eclectic_by_dimension(all_data, dimension)
        if eclectic_df.empty:
            return {"table_html": "<p class='text-muted text-sm'>No data available.</p>"}
        formatted = format_eclectic_table(eclectic_df, display_dim)
        return {"table_html": _df_to_html(formatted)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/eclectic")
async def eclectic_page(request: Request):
    ctx = _eclectic_tab_context("Player")
    return templates.TemplateResponse("eclectic.html", {
        "request": request,
        "active_page": "scorecards",
        "tabs": ECLECTIC_TABS,
        "active_tab": "Player",
        **ctx,
    })


@router.get("/eclectic/tab")
async def eclectic_tab(request: Request, dimension: str = Query("Player")):
    ctx = _eclectic_tab_context(dimension)
    return templates.TemplateResponse("partials/eclectic_tab.html", {
        "request": request,
        **ctx,
    })
