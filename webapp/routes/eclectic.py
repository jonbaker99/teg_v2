"""Eclectic routes: /eclectic."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.eclectic import (
    calculate_eclectic_by_dimension,
    format_eclectic_table,
    get_overall_top_eclectics,
    get_personal_best_eclectics,
    format_eclectic_records_table,
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


# --- Eclectic Records ---------------------------------------------------------

ECLECTIC_RECORDS_TABS = [
    ("TEGNum", "TEGs"),
    ("Course", "Courses"),
]


def _eclectic_records_context(dimension: str) -> dict:
    """Build context for an eclectic-records tab (Top 3 + Personal Best tables)."""
    try:
        all_data = cached_load_all_data()
        dim_label = "TEG" if dimension == "TEGNum" else dimension

        top = get_overall_top_eclectics(all_data, dimension, top_n=3)
        pb = get_personal_best_eclectics(all_data, dimension)

        sections = [
            {
                "title": f"Top 3 {dim_label} Eclectics",
                "table_html": _df_to_html(format_eclectic_records_table(top)),
            },
            {
                "title": f"Personal Best {dim_label} Eclectics",
                "table_html": _df_to_html(format_eclectic_records_table(pb)),
            },
        ]
        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/eclectic-records")
async def eclectic_records_page(request: Request):
    default_tab = "TEGNum"
    ctx = _eclectic_records_context(default_tab)
    return templates.TemplateResponse("eclectic_records.html", {
        "request": request,
        "active_page": "scorecards",
        "tabs": ECLECTIC_RECORDS_TABS,
        "active_tab": default_tab,
        **ctx,
    })


@router.get("/eclectic-records/tab")
async def eclectic_records_tab(request: Request, dimension: str = Query("TEGNum")):
    ctx = _eclectic_records_context(dimension)
    return templates.TemplateResponse("partials/eclectic_records_tab.html", {
        "request": request,
        **ctx,
    })
