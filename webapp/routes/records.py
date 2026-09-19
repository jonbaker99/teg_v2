"""Records routes."""

import re
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

# Sentinel values used in place of a player identity when a record is shared
# by 3+ people (see prepare_streak_records_table / prepare_score_count_records_table):
# the "who" moves into the other detail column as an initials list instead.
# Used to correct the per-row exception below.
_PLACEHOLDER_IDENTITY_RE = re.compile(r'^\(\d+\s+times?\)$')


def _is_placeholder_identity(val) -> bool:
    val_str = str(val).strip()
    return val_str == '→' or bool(_PLACEHOLDER_IDENTITY_RE.match(val_str))


def _pick_detail_col_idx(df: pd.DataFrame, cols: list, candidates: list) -> int:
    """Of the two non-value/title columns, pick the one that's the long
    "detail" (venue/date) string to collapse behind a tap, vs. the short
    "identity" (name) one always shown -- e.g. teg/round/9hole put the name
    in column 2 and venue/date in column 3, every row, consistently. Decided
    once per render from average string length, not re-derived per row: for
    those tabs the two columns play a fixed role throughout the table.

    Streaks/score_counts break that column-level consistency: whenever a
    record is shared by 3+ people, the "name" column holds a placeholder
    ('->' or '(N times)') and the *other* column holds the real identity
    (an initials list), row by row within the same table. So this picks a
    per-table default by average length, and the caller applies a narrow,
    per-row override only for those placeholder values -- not a second
    general heuristic, just correcting the one known exception.
    """
    if len(candidates) != 2:
        return candidates[-1] if candidates else -1
    a, b = candidates
    avg_len_a = df[cols[a]].dropna().astype(str).str.len().mean() if not df.empty else 0
    avg_len_b = df[cols[b]].dropna().astype(str).str.len().mean() if not df.empty else 0
    return b if avg_len_b >= avg_len_a else a


def _build_records_html(df: pd.DataFrame) -> str:
    """Convert a records DataFrame to a styled HTML table (desktop/iPad,
    unchanged) plus a mobile-only tap-to-reveal list of the same rows.
    mobile.css shows exactly one of the two per breakpoint (same
    dual-markup + CSS-toggle mechanism as .lb-table-card/.lb-cards)."""
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

    # The remaining columns (not the title, not the value) are the
    # identity/detail pair the mobile list needs to tell apart. A caller
    # with no real "detail" data (e.g. latest.py's single-round/TEG record
    # summaries, which have nothing like /records' venue+date "when") may
    # pass only one such column -- that one is always identity, with an
    # empty (but present) detail panel, rather than risk the length
    # heuristic below misreading an always-empty filler column as identity.
    other_idx = [i for i in range(1, len(cols)) if i != value_col_idx]
    detail_col_idx = _pick_detail_col_idx(df, cols, other_idx) if len(other_idx) == 2 else None
    identity_col_idx = None
    if detail_col_idx is not None:
        identity_col_idx = [i for i in other_idx if i != detail_col_idx][0]
    elif len(other_idx) == 1:
        identity_col_idx = other_idx[0]

    rows = []
    rows.append("<table class='records-table records-table--borderless'>")
    list_items = []

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

        # Mobile row: same label/value, but identity vs. detail swap per-row
        # when the "identity" slot actually holds a shared-record placeholder
        # (see _is_placeholder_identity) -- the initials list in the other
        # column is the real answer to "who" for those rows.
        label_html = row[cols[0]] if show_title else ""
        value_html = row[cols[value_col_idx]] if value_col_idx is not None else ""
        if identity_col_idx is not None:
            id_val = row[cols[identity_col_idx]]
            det_val = row[cols[detail_col_idx]] if detail_col_idx is not None else ""
            if detail_col_idx is not None and _is_placeholder_identity(id_val):
                id_val, det_val = det_val, id_val
        else:
            id_val, det_val = "", ""

        if detail_col_idx is None:
            # No real detail to reveal (e.g. latest.py's single-record
            # summaries) -- render a plain, non-expandable row: no chevron,
            # no tap affordance, no empty <details> to open onto nothing.
            list_items.append(
                "<div class='rec-row rec-row--flat'>"
                "<div class='rec-summary rec-summary--flat'>"
                f"<span class='rec-label'>{label_html}</span>"
                f"<span class='rec-value'>{value_html}</span>"
                f"<span class='rec-identity'>{id_val}</span>"
                "</div>"
                "</div>"
            )
        else:
            list_items.append(
                "<details class='rec-row'>"
                "<summary class='rec-summary'>"
                f"<span class='rec-label'>{label_html}</span>"
                f"<span class='rec-value'>{value_html}</span>"
                f"<span class='rec-identity'>{id_val}</span>"
                "<span class='rec-chevron' aria-hidden='true'></span>"
                "</summary>"
                f"<div class='rec-detail'>{det_val}</div>"
                "</details>"
            )

    rows.append("</tbody></table>")
    rows.append("<div class='records-list'>")
    rows.extend(list_items)
    rows.append("</div>")
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
        caption = None

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
            caption = "* and counting..."

        elif tab_name == "score_counts":
            all_data = cached_load_all_data()
            best_df, worst_df = prepare_score_count_records_table(all_data)
            sections.append(_section("Best Score Counts", best_df))
            sections.append(_section("Worst Score Counts", worst_df))
            caption = "Eagles, Birdies and Pars also include better scores"

        return {"sections": sections, "caption": caption}

    except Exception as e:
        return {"error": str(e)}


@router.get("/records")
def records_page(request: Request):
    ctx = _tab_context("teg")
    return templates.TemplateResponse("records.html", {
        "request": request,
        "active_page": "records",
        "tabs": TABS,
        "active_tab": "teg",
        **ctx,
    })


@router.get("/records/tab/{tab_name}")
def records_tab(request: Request, tab_name: str):
    ctx = _tab_context(tab_name)
    return templates.TemplateResponse("partials/records_tab.html", {
        "request": request,
        **ctx,
    })
