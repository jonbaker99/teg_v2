"""Performance section routes: /top-performances, /personal-bests."""

import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.analysis.rankings import get_ranked_teg_data, get_ranked_round_data
from teg_analysis.analysis.records import identify_aggregate_records_and_pbs
from teg_analysis.display.formatters import prepare_records_table
from webapp.deps import (
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_ranked_frontback_data,
    cached_complete_teg_data,
    cached_round_data,
    get_filtered_teg_data,
)
from webapp.tables import df_to_html as _df_to_html, EMPTY_TABLE_HTML

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# --- /top-performances --------------------------------------------------------

TOP_TABS = [
    ("best_teg", "Best TEGs"),
    ("best_round", "Best Rounds"),
    ("worst_teg", "Worst TEGs"),
    ("worst_round", "Worst Rounds"),
]

TOP_MEASURES = [
    ("GrossVP", "Gross"),
    ("Sc", "Score"),
    ("NetVP", "Net"),
    ("Stableford", "Stableford"),
]


def _build_top_performances_byline_html(display: pd.DataFrame, id_cols: list) -> str:
    """Mobile-only byline-row list for Top Performances.

    The desktop table gives the 6 id/location columns equal width, which is
    fine on a wide screen but overflows badly on a phone (Area/Course text is
    often longer than its ~1/6 share). Below 640px (mobile.css) we swap to
    this list instead: the primary line (#, Player, measure value) stays the
    at-a-glance leaderboard fact, and the id_cols collapse onto one muted
    sub-line so the row still fits without truncating any of the data.
    Mirrors the .sc-landscape/.sc-portrait dual-markup + CSS-toggle pattern
    used elsewhere (build_bestball_worstball_responsive et al.) rather than
    trying to reflow the table itself.
    """
    if display is None or display.empty:
        return ""

    cols = list(display.columns)
    measure_col = cols[2]  # '#', 'Player', <measure friendly name>, *id_cols

    rows_html = ['<div class="tp-list">']
    for _, row in display.iterrows():
        rank = escape(str(row['#']))
        player_name = str(row['Player'])
        # Player profiles hidden 2026-09-18: pages not ready to be live, so
        # this renders plain text rather than a `/player/<code>` link.
        player_html = escape(player_name)
        value = escape(str(row[measure_col]))
        sub = " · ".join(escape(str(row[c])) for c in id_cols)
        rows_html.append(
            '<div class="tp-row">'
            f'<div class="tp-top"><span class="tp-rank">{rank}</span>'
            f'<span class="tp-player">{player_html}</span>'
            f'<span class="tp-value">{value}</span></div>'
            f'<div class="tp-sub">{sub}</div>'
            '</div>'
        )
    rows_html.append('</div>')
    return ''.join(rows_html)


def _top_tab_context(tab: str, measure: str = "GrossVP", n: int = 3) -> dict:
    try:
        is_teg = "teg" in tab
        is_worst = "worst" in tab

        measure_friendly = dict(TOP_MEASURES).get(measure, measure)

        if is_teg:
            data = get_filtered_teg_data()
        else:
            data = cached_ranked_round_data()

        # Sort direction:
        # "Best" means lowest for GrossVP/NetVP/Sc, highest for Stableford
        # "Worst" is the reverse
        higher_is_better = (measure == 'Stableford')
        if is_worst:
            ascending = higher_is_better  # worst stableford = ascending (lowest)
        else:
            ascending = not higher_is_better  # best stableford = descending (highest)

        sorted_data = data.sort_values(measure, ascending=ascending).head(n)
        sorted_data = sorted_data.copy()
        sorted_data.insert(0, '#', range(1, len(sorted_data) + 1))

        if is_teg:
            sorted_data['TEG'] = 'TEG ' + sorted_data['TEGNum'].astype(int).astype(str)
            id_cols = ['TEG']
            if 'Area' in sorted_data.columns:
                id_cols.append('Area')
            if 'Year' in sorted_data.columns:
                id_cols.append('Year')
        else:
            sorted_data['Round'] = 'TEG ' + sorted_data['TEGNum'].astype(int).astype(str) + '|R' + sorted_data['Round'].astype(int).astype(str)
            id_cols = ['Round']
            if 'Course' in sorted_data.columns:
                id_cols.append('Course')
            if 'Year' in sorted_data.columns:
                id_cols.append('Year')

        # Rename measure column to friendly name
        sorted_data = sorted_data.rename(columns={measure: measure_friendly})

        display_cols = ['#', 'Player', measure_friendly] + id_cols
        display = sorted_data[display_cols].copy()

        # Format measure values
        display = _format_measure_col(display, measure, measure_friendly)

        prefix = "Bottom" if is_worst else "Top"
        noun = "TEGs" if is_teg else "Rounds"
        label = f"{prefix} {n} {noun}: {measure_friendly}"
        caption = ("Note: TEG 2 is excluded from all TEG-level analysis as it only had "
                   "3 rounds compared to the standard 4 rounds.") if is_teg else None
        table_html = (
            f'<div class="tp-table">{_df_to_html(display)}</div>'
            f'{_build_top_performances_byline_html(display, id_cols)}'
        )
        sections = [{"title": label, "table_html": table_html}]
        return {"sections": sections, "caption": caption}
    except Exception as e:
        logger.exception("_top_tab_context failed")
        return {"error": str(e)}


@router.get("/top-performances")
def top_performances_page(
    request: Request,
    tab: str = Query("best_teg"),
    measure: str = Query("GrossVP"),
    n: int = Query(3),
):
    tab = tab if tab in {tab_id for tab_id, _label in TOP_TABS} else "best_teg"
    measure = measure if measure in dict(TOP_MEASURES) else "GrossVP"
    n = n if 1 <= n <= 100 else 3
    ctx = _top_tab_context(tab, measure, n)
    return templates.TemplateResponse("top_performances.html", {
        "request": request,
        "active_page": "top-performances",
        "tabs": TOP_TABS,
        "active_tab": tab,
        "measures": TOP_MEASURES,
        "selected_measure": measure,
        "n_records": n,
        **ctx,
    })


@router.get("/top-performances/tab")
def top_performances_tab(request: Request, tab: str = "best_teg", measure: str = "GrossVP", n: int = 3):
    ctx = _top_tab_context(tab, measure, n)
    return templates.TemplateResponse("partials/top_performances_tab.html", {
        "request": request,
        **ctx,
    })


# --- /personal-bests ----------------------------------------------------------

PB_TABS = [
    ("pb_summary", "PB Summary"),
    ("best_tegs", "Best TEGs"),
    ("best_rounds", "Best Rounds"),
    ("worst_tegs", "Worst TEGs"),
    ("worst_rounds", "Worst Rounds"),
]

PB_MEASURES = [
    ("GrossVP", "Gross"),
    ("Sc", "Score"),
    ("NetVP", "Net"),
    ("Stableford", "Stableford"),
]

# Summary sub-views for the PB Summary tab
PB_SUMMARY_VIEWS = [
    ("rounds", "Best Rounds"),
    ("tegs", "Best TEGs"),
    ("nines", "Best 9s"),
]


def _format_vs_par(value) -> str:
    """Format a vs-par value with +/- notation."""
    from teg_analysis.display.formatters import format_vs_par as _fvp
    return _fvp(value)


def _format_measure_col(df: pd.DataFrame, measure: str, friendly_name: str) -> pd.DataFrame:
    """Format the measure column for display."""
    df = df.copy()
    if friendly_name in ('Gross', 'Net', 'Gross vs Par', 'Net vs Par'):
        df[friendly_name] = df[friendly_name].apply(_format_vs_par)
    else:
        # Convert numeric columns to int for clean display
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            if col != '#':
                df[col] = df[col].astype(int)
    return df


def _pb_summary_html(df: pd.DataFrame, cell_classes: dict) -> str:
    """Render the PB Summary table with two-line measure cells.

    Every measure cell (Score/Gross/Net/Stfd) is a ``(value, context)`` tuple
    -- e.g. ``("88", "TEG 10|R4")`` -- rather than one concatenated string,
    because at phone width the concatenated form ("88 (TEG 10|R4)") doesn't
    fit and overflows (see mobile.css's ".pbv"/".pbc" rules, which stack and
    center the two lines below 640px; above that, the CSS just puts them on
    one line, matching the old plain-string look). ``df_to_html`` only knows
    how to escape a single scalar per cell, so this is a small dedicated
    renderer for this one table rather than teaching it nested spans. Mirrors
    df_to_html's own structure/escaping (webapp/tables.py) -- same header
    loop, same cell_classes override, same not-a-generic-API scope.
    """
    if df is None or df.empty:
        return EMPTY_TABLE_HTML

    cols = list(df.columns)
    rows = ["<table class='teg-table'><thead><tr>"]
    for col in cols:
        rows.append(f"<th>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for row_idx, (_, row) in enumerate(df.iterrows()):
        rows.append("<tr>")
        for col in cols:
            cls = cell_classes.get((row_idx, col)) if cell_classes else None
            cls_attr = f" class='{cls}'" if cls else ""
            val = row[col]
            if isinstance(val, tuple):
                value_str, context_str = val
                # The " (" / ")" separators are plain text nodes (not CSS
                # content) so that with no CSS at all -- i.e. desktop/iPad,
                # where .pbv/.pbc/.pb-sep get no rules outside the mobile
                # media query -- the cell reads exactly as the old
                # concatenated string ("88 (TEG 10|R4)"), byte-for-byte the
                # same rendered text. Mobile hides .pb-sep and stacks
                # .pbv/.pbc as two centered lines instead.
                rows.append(
                    f"<td{cls_attr}><span class='pbv'>{escape(str(value_str))}</span>"
                    f"<span class='pb-sep'> (</span>"
                    f"<span class='pbc'>{escape(str(context_str))}</span>"
                    f"<span class='pb-sep'>)</span></td>"
                )
            else:
                rows.append(f"<td{cls_attr}>{escape(str(val))}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _pb_summary_context(view: str = "rounds") -> dict:
    """Build PB summary table: one row per player, columns for each measure."""
    try:
        if view == "tegs":
            data = get_filtered_teg_data()
            level = "teg"
        elif view == "nines":
            data = cached_ranked_frontback_data()
            level = "nines"
        else:
            data = cached_ranked_round_data()
            level = "round"

        players = sorted(data['Player'].unique())
        summary_rows = []
        best_numeric = {}  # player -> {measure_col: numeric best} for record detection

        for player in players:
            pdata = data[data['Player'] == player]
            row = {'Player': player}

            if level == "teg":
                def _when_teg(r):
                    return f"TEG {int(r['TEGNum'])}"
            elif level == "nines":
                def _when_nines(r):
                    return f"TEG {int(r['TEGNum'])}|R{int(r['Round'])}|{r['FrontBack']}"
            else:
                def _when_round(r):
                    return f"TEG {int(r['TEGNum'])}|R{int(r['Round'])}"

            def _when(r):
                if level == "teg":
                    return _when_teg(r)
                elif level == "nines":
                    return _when_nines(r)
                else:
                    return _when_round(r)

            # Each measure cell is a (value, context) tuple -- e.g.
            # ("88", "TEG 10|R4") -- rendered as a two-line cell by
            # _pb_summary_html, rather than one concatenated string that
            # overflows at phone width.

            # Score (lowest is best)
            best_sc = pdata.loc[pdata['Sc'].idxmin()]
            row['Score'] = (str(int(best_sc['Sc'])), _when(best_sc))

            # Gross vs Par (lowest is best)
            best_g = pdata.loc[pdata['GrossVP'].idxmin()]
            row['Gross'] = (_format_vs_par(best_g['GrossVP']), _when(best_g))

            # Net vs Par (lowest is best)
            best_n = pdata.loc[pdata['NetVP'].idxmin()]
            row['Net'] = (_format_vs_par(best_n['NetVP']), _when(best_n))

            # Stableford (highest is best)
            best_s = pdata.loc[pdata['Stableford'].idxmax()]
            row['Stfd'] = (str(int(best_s['Stableford'])), _when(best_s))

            best_numeric[player] = {
                'Score': int(best_sc['Sc']),
                'Gross': best_g['GrossVP'],
                'Net': best_n['NetVP'],
                'Stfd': int(best_s['Stableford']),
            }

            summary_rows.append(row)

        display = pd.DataFrame(summary_rows)

        # Identify the overall record-holder cell(s) per measure column so the
        # template can highlight them (lowest Score/Gross/Net, highest Stfd).
        records = {
            'Score': min(v['Score'] for v in best_numeric.values()),
            'Gross': min(v['Gross'] for v in best_numeric.values()),
            'Net': min(v['Net'] for v in best_numeric.values()),
            'Stfd': max(v['Stfd'] for v in best_numeric.values()),
        }
        cell_classes = {}
        for i, player in enumerate(players):
            for col, rec in records.items():
                if best_numeric[player][col] == rec:
                    cell_classes[(i, col)] = 'pb-record'

        if view == "tegs":
            title = "Personal Best TEGs"
        elif view == "nines":
            title = "Personal Best 9s"
        else:
            title = "Personal Best Rounds"
        sections = [{"title": title, "table_html": _pb_summary_html(display, cell_classes)}]
        return {"sections": sections}
    except Exception as e:
        logger.exception("_pb_summary_context failed")
        return {"error": str(e)}


def _pb_tab_context(tab: str, measure: str = "GrossVP", n: int = 3) -> dict:
    """Build data for a personal-bests tab (best/worst TEGs/rounds)."""
    try:
        is_teg = "teg" in tab
        is_worst = "worst" in tab

        # Map internal measure name to friendly name
        measure_friendly = dict(PB_MEASURES).get(measure, measure)

        if is_teg:
            data = get_filtered_teg_data()
        else:
            data = cached_ranked_round_data()

        # Determine sort direction:
        # "Best" means lowest for GrossVP/NetVP/Sc, highest for Stableford
        # "Worst" is the reverse
        higher_is_better = (measure == 'Stableford')
        if is_worst:
            ascending = higher_is_better  # worst stableford = ascending (lowest)
        else:
            ascending = not higher_is_better  # best stableford = descending (highest)

        # Get best/worst n per player
        sorted_data = data.sort_values(measure, ascending=ascending)
        result = sorted_data.groupby('Player').head(n).sort_values(
            ['Player', measure], ascending=[True, ascending]
        )

        # Build display columns
        if is_teg:
            result = result.copy()
            result['TEG'] = 'TEG ' + result['TEGNum'].astype(int).astype(str)
            id_cols = ['TEG']
            if 'Area' in result.columns:
                id_cols.append('Area')
            if 'Year' in result.columns:
                id_cols.append('Year')
        else:
            result = result.copy()
            result['Round_Label'] = 'TEG ' + result['TEGNum'].astype(int).astype(str) + '|R' + result['Round'].astype(int).astype(str)
            id_cols = ['Round_Label']
            if 'Course' in result.columns:
                id_cols.append('Course')
            if 'Year' in result.columns:
                id_cols.append('Year')

        # Rename measure column to friendly name
        result = result.rename(columns={measure: measure_friendly})
        if 'Round_Label' in result.columns:
            # Drop the numeric Round so the 'TEG x|Ry' label can take the name
            # without producing a duplicate 'Round' column.
            if 'Round' in result.columns:
                result = result.drop(columns=['Round'])
            result = result.rename(columns={'Round_Label': 'Round'})
            id_cols = ['Round' if c == 'Round_Label' else c for c in id_cols]

        display_cols = ['Player', measure_friendly] + id_cols
        display = result[display_cols].copy()

        # Format measure values
        display = _format_measure_col(display, measure, measure_friendly)

        label = f"{'Worst' if is_worst else 'Best'} {'TEGs' if is_teg else 'Rounds'} \u2014 {measure_friendly}"
        sections = [{"title": label, "table_html": _df_to_html(display)}]
        return {"sections": sections}
    except Exception as e:
        logger.exception("_pb_tab_context failed")
        return {"error": str(e)}


@router.get("/personal-bests")
def personal_bests_page(
    request: Request,
    tab: str = Query("pb_summary"),
    measure: str = Query("GrossVP"),
    n: int = Query(1),
    view: str = Query("rounds"),
):
    tab = tab if tab in {tab_id for tab_id, _label in PB_TABS} else "pb_summary"
    measure = measure if measure in dict(PB_MEASURES) else "GrossVP"
    n = n if 1 <= n <= 100 else 1
    view = view if view in {view_id for view_id, _label in PB_SUMMARY_VIEWS} else "rounds"

    if tab == "pb_summary":
        ctx = _pb_summary_context(view)
    else:
        ctx = _pb_tab_context(tab, measure, n)

    return templates.TemplateResponse("personal_bests.html", {
        "request": request,
        "active_page": "personal-bests",
        "tabs": PB_TABS,
        "active_tab": tab,
        "measures": PB_MEASURES,
        "selected_measure": measure,
        "n_records": n,
        "summary_views": PB_SUMMARY_VIEWS,
        "selected_view": view,
        **ctx,
    })


@router.get("/personal-bests/tab")
def personal_bests_tab(
    request: Request,
    tab: str = "pb_summary",
    measure: str = "GrossVP",
    n: int = 1,
    view: str = "rounds",
):
    if tab == "pb_summary":
        ctx = _pb_summary_context(view)
    else:
        ctx = _pb_tab_context(tab, measure, n)
    return templates.TemplateResponse("partials/personal_bests_tab.html", {
        "request": request,
        **ctx,
    })
