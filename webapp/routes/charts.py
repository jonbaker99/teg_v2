"""Charts routes."""

from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.deps import cached_load_all_data, get_default_teg_num, get_available_teg_numbers
from webapp.chart_utils import (
    create_cumulative_graph,
    adjusted_stableford,
    adjusted_grossvp,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

CHART_TYPES = [
    ("stableford", "Stableford"),
    ("gross", "Gross vs Par"),
    ("stableford_adj", "Stableford (Adjusted)"),
    ("gross_adj", "Gross (Adjusted)"),
]

CHART_CONFIGS = {
    "stableford": {
        "y_series": "Stableford Cum TEG",
        "title": "Cumulative Stableford",
        "y_calculation": None,
        "y_axis_label": "Stableford Points",
        "chart_type": "stableford",
    },
    "gross": {
        "y_series": "GrossVP Cum TEG",
        "title": "Cumulative Gross vs Par",
        "y_calculation": None,
        "y_axis_label": "Gross vs Par",
        "chart_type": "gross",
    },
    "stableford_adj": {
        "y_series": "Stableford Cum TEG",
        "title": "Adjusted Stableford (vs 2-per-hole pace)",
        "y_calculation": adjusted_stableford,
        "y_axis_label": "Stableford (Adjusted)",
        "chart_type": "stableford",
    },
    "gross_adj": {
        "y_series": "GrossVP Cum TEG",
        "title": "Adjusted Gross vs Par (vs +1-per-hole pace)",
        "y_calculation": adjusted_grossvp,
        "y_axis_label": "Gross vs Par (Adjusted)",
        "chart_type": "gross",
    },
}


def _chart_context(teg_num: int, chart_type: str) -> dict:
    """Build chart context for a given TEG and chart type."""
    try:
        config = CHART_CONFIGS.get(chart_type, CHART_CONFIGS["stableford"])
        df = cached_load_all_data()
        teg_name = f"TEG {teg_num}"

        fig = create_cumulative_graph(
            df,
            teg_name,
            config["y_series"],
            config["title"],
            y_calculation=config["y_calculation"],
            y_axis_label=config["y_axis_label"],
            chart_type=config["chart_type"],
        )

        return {
            "chart_title": config["title"],
            "figure_json": fig.to_json(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/charts")
async def charts_page(request: Request, type: str = "stableford"):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _chart_context(teg_num, type)
    return templates.TemplateResponse("charts.html", {
        "request": request,
        "active_page": "charts",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "selected_type": type,
        "chart_types": CHART_TYPES,
        **ctx,
    })


@router.get("/charts/figure")
async def charts_figure(request: Request, teg: int = Query(...), type: str = "stableford"):
    ctx = _chart_context(teg, type)
    return templates.TemplateResponse("partials/chart_container.html", {
        "request": request,
        **ctx,
    })
