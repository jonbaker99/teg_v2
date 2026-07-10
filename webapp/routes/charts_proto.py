"""Chart style prototype — dev-only page showing all named styles side by side."""

from pathlib import Path

from fastapi import APIRouter, Request

from fastapi.templating import Jinja2Templates

from webapp.deps import cached_load_all_data, get_default_teg_num
from webapp.chart_utils import (
    create_cumulative_graph,
    CHART_STYLES,
    CHART_STYLE_META,
    get_chart_style,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/charts-proto")
def charts_proto(request: Request):
    df = cached_load_all_data()
    teg_num = get_default_teg_num()
    teg_name = f"TEG {teg_num}"

    charts = []
    for style_key in CHART_STYLES:
        label, description = CHART_STYLE_META[style_key]
        try:
            fig = create_cumulative_graph(
                df,
                teg_name,
                y_series="GrossVP Cum TEG",
                title=f"Cumulative Gross vs Par — {teg_name}",
                y_axis_label="Gross vs Par",
                chart_type="gross",
                plotly_theme=get_chart_style(style_key),
            )
            figure_json = fig.to_json()
        except Exception as e:
            figure_json = None
            label = f"{label} (error: {e})"

        charts.append({
            "style_key": style_key,
            "label": label,
            "description": description,
            "figure_json": figure_json,
        })

    return templates.TemplateResponse("charts_proto.html", {
        "request": request,
        "active_page": "charts-proto",
        "teg_name": teg_name,
        # Realistic title/subtitle so each card reads like the live Streamlit page
        # (the data shown is the gross-vs-par "Green Jacket race").
        "chart_title": f"Green Jacket race: {teg_name}",
        "chart_subtitle": "Cumulative gross score vs. par | Lower = better",
        "charts": charts,
    })
