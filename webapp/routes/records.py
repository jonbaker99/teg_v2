"""Records routes."""

from pathlib import Path

import pandas as pd
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

# Columns that should be right-aligned (numeric content)
_NUMERIC_COLS = {
    'Score', 'Gross', 'Net', 'Stableford', 'Pts', 'Points', 'Total',
    'Vs Par', 'GrossVP', 'NetVP', 'Count', 'Rounds', 'TEGs',
    'Streak', 'Length', 'Best', 'Worst', 'Avg', 'Average',
}

# Columns that should be centered (rank-like)
_RANK_COLS = {'Rank', '#', ''}


def _build_records_html(df: pd.DataFrame) -> str:
    """Convert a records DataFrame to a styled HTML table with alignment classes."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    cols = list(df.columns)
    # Determine which column index holds the score value (first numeric-like column)
    value_col_idx = None
    for i, col in enumerate(cols):
        col_str = str(col).strip()
        if col_str in _NUMERIC_COLS or (col_str in _RANK_COLS and i > 0) or _looks_numeric(df, col):
            value_col_idx = i
            break

    rows = []
    rows.append("<table class='records-table records-table--borderless'>")

    prev_title = None
    for _, row in df.iterrows():
        title_val = row[cols[0]]
        if title_val != prev_title:
            if prev_title is not None:
                rows.append("</tbody>")
            rows.append("<tbody>")
            prev_title = title_val
            show_title = True
        else:
            show_title = False

        rows.append("<tr>")
        for i, col in enumerate(cols):
            val = row[col]
            if i == 0:
                if show_title:
                    rows.append(f"<td class='col-player'>{val}</td>")
                else:
                    rows.append("<td class='col-player'></td>")
            elif i == value_col_idx:
                rows.append(f"<td class='col-num' style='font-weight:700'>{val}</td>")
            else:
                rows.append(f"<td class='col-player'>{val}</td>")
        rows.append("</tr>")

    rows.append("</tbody></table>")
    return "".join(rows)


def _looks_numeric(df: pd.DataFrame, col: str) -> bool:
    """Check if a column's non-null values are numeric."""
    try:
        sample = df[col].dropna().head(5)
        if sample.empty:
            return False
        if pd.api.types.is_numeric_dtype(sample):
            return True
        # Try converting string values
        pd.to_numeric(sample.astype(str).str.replace('=', '', regex=False), errors='raise')
        return True
    except (ValueError, TypeError):
        return False


def _section(title: str, df) -> dict:
    """Build a section dict with title, HTML table and record count."""
    return {
        "title": title,
        "table_html": _build_records_html(df),
        "record_count": len(df) if df is not None and not df.empty else 0,
    }


def _tab_context(tab_name: str) -> dict:
    """Build context for a records tab."""
    try:
        sections = []

        if tab_name == "teg":
            ranked = cached_ranked_teg_data()
            best = prepare_records_table(ranked, 'teg')
            sections.append(_section("Best TEGs", best))

            filtered = get_filtered_teg_data()
            worst = prepare_worst_records_table(filtered, 'teg')
            sections.append(_section("Worst TEGs", worst))

        elif tab_name == "round":
            ranked = cached_ranked_round_data()
            best = prepare_records_table(ranked, 'round')
            sections.append(_section("Best Rounds", best))

            rd_data = cached_round_data()
            worst = prepare_worst_records_table(rd_data, 'round')
            sections.append(_section("Worst Rounds", worst))

        elif tab_name == "9hole":
            ranked = cached_ranked_frontback_data()
            best = prepare_records_table(ranked, 'frontback')
            sections.append(_section("Best 9-Hole Scores", best))

            nine_data = cached_9_data()
            worst = prepare_worst_records_table(nine_data, 'frontback')
            sections.append(_section("Worst 9-Hole Scores", worst))

        elif tab_name == "streaks":
            all_data = cached_load_all_data()

            best_streaks = prepare_record_best_streaks_data(all_data)
            best_table = prepare_streak_records_table(best_streaks, "Best Streaks:")
            sections.append(_section("Best Streaks", best_table))

            worst_streaks = prepare_record_worst_streaks_data(all_data)
            worst_table = prepare_streak_records_table(worst_streaks, "Worst Streaks:")
            sections.append(_section("Worst Streaks", worst_table))

        elif tab_name == "score_counts":
            all_data = cached_load_all_data()
            best_df, worst_df = prepare_score_count_records_table(all_data)
            sections.append(_section("Best Score Counts", best_df))
            sections.append(_section("Worst Score Counts", worst_df))

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
