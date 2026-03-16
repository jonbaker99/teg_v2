"""Records routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from webapp.deps import (
    cached_load_all_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_ranked_frontback_data,
    cached_round_data,
    cached_9_data,
    get_filtered_teg_data,
)
from teg_analysis.display.formatters import (
    prepare_records_table,
    prepare_worst_records_table,
    prepare_streak_records_table,
    prepare_score_count_records_table,
)
from teg_analysis.analysis.streaks import (
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

TABS = [
    ("teg", "TEG Records"),
    ("round", "Round Records"),
    ("9hole", "9-Hole Records"),
    ("streaks", "Streaks"),
    ("score_counts", "Score Counts"),
]


def _df_to_html(df):
    """Convert a DataFrame to a styled HTML table."""
    if df is None or df.empty:
        return "<p class='text-gray-500 text-sm'>No data available.</p>"
    return df.to_html(escape=False, index=False, classes="records-table")


def _tab_context(tab_name: str) -> dict:
    """Build context for a records tab."""
    try:
        sections = []

        if tab_name == "teg":
            ranked = cached_ranked_teg_data()
            best = prepare_records_table(ranked, 'teg')
            sections.append({"title": "Best TEGs", "table_html": _df_to_html(best)})

            filtered = get_filtered_teg_data()
            worst = prepare_worst_records_table(filtered, 'teg')
            sections.append({"title": "Worst TEGs", "table_html": _df_to_html(worst)})

        elif tab_name == "round":
            ranked = cached_ranked_round_data()
            best = prepare_records_table(ranked, 'round')
            sections.append({"title": "Best Rounds", "table_html": _df_to_html(best)})

            rd_data = cached_round_data()
            worst = prepare_worst_records_table(rd_data, 'round')
            sections.append({"title": "Worst Rounds", "table_html": _df_to_html(worst)})

        elif tab_name == "9hole":
            ranked = cached_ranked_frontback_data()
            best = prepare_records_table(ranked, 'frontback')
            sections.append({"title": "Best 9-Hole Scores", "table_html": _df_to_html(best)})

            nine_data = cached_9_data()
            worst = prepare_worst_records_table(nine_data, 'frontback')
            sections.append({"title": "Worst 9-Hole Scores", "table_html": _df_to_html(worst)})

        elif tab_name == "streaks":
            all_data = cached_load_all_data()

            best_streaks = prepare_record_best_streaks_data(all_data)
            best_table = prepare_streak_records_table(best_streaks, "Best Streaks:")
            sections.append({"title": "Best Streaks", "table_html": _df_to_html(best_table)})

            worst_streaks = prepare_record_worst_streaks_data(all_data)
            worst_table = prepare_streak_records_table(worst_streaks, "Worst Streaks:")
            sections.append({"title": "Worst Streaks", "table_html": _df_to_html(worst_table)})

        elif tab_name == "score_counts":
            all_data = cached_load_all_data()
            best_df, worst_df = prepare_score_count_records_table(all_data)
            sections.append({"title": "Best Score Counts", "table_html": _df_to_html(best_df)})
            sections.append({"title": "Worst Score Counts", "table_html": _df_to_html(worst_df)})

        return {"sections": sections}

    except Exception as e:
        return {"error": str(e)}


@router.get("/records")
async def records_page(request: Request):
    ctx = _tab_context("teg")
    return templates.TemplateResponse("records.html", {
        "request": request,
        "active_page": "records",
        "tabs": TABS,
        "active_tab": "teg",
        **ctx,
    })


@router.get("/records/tab/{tab_name}")
async def records_tab(request: Request, tab_name: str):
    ctx = _tab_context(tab_name)
    return templates.TemplateResponse("partials/records_tab.html", {
        "request": request,
        **ctx,
    })
