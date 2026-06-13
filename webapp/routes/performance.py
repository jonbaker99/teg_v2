"""Performance section routes: /top-performances, /personal-bests."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

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

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table", cell_classes=None) -> str:
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"
    rows = [f"<table class='{table_class}'><thead><tr>"]
    for col in df.columns:
        rows.append(f"<th>{col}</th>")
    rows.append("</tr></thead><tbody>")
    for i, (_, row) in enumerate(df.iterrows()):
        rows.append("<tr>")
        for col in df.columns:
            cls = cell_classes.get((i, col)) if cell_classes else None
            cls_attr = f" class='{cls}'" if cls else ""
            rows.append(f"<td{cls_attr}>{row[col]}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


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
        sections = [{"title": label, "table_html": _df_to_html(display)}]
        return {"sections": sections, "caption": caption}
    except Exception as e:
        return {"error": str(e)}


@router.get("/top-performances")
async def top_performances_page(request: Request):
    default_tab = "best_teg"
    default_measure = "GrossVP"
    default_n = 3
    ctx = _top_tab_context(default_tab, default_measure, default_n)
    return templates.TemplateResponse("top_performances.html", {
        "request": request,
        "active_page": "top-performances",
        "tabs": TOP_TABS,
        "active_tab": default_tab,
        "measures": TOP_MEASURES,
        "selected_measure": default_measure,
        "n_records": default_n,
        **ctx,
    })


@router.get("/top-performances/tab")
async def top_performances_tab(request: Request, tab: str = "best_teg", measure: str = "GrossVP", n: int = 3):
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

            # Score (lowest is best)
            best_sc = pdata.loc[pdata['Sc'].idxmin()]
            row['Score'] = f"{int(best_sc['Sc'])} ({_when(best_sc)})"

            # Gross vs Par (lowest is best)
            best_g = pdata.loc[pdata['GrossVP'].idxmin()]
            row['Gross'] = f"{_format_vs_par(best_g['GrossVP'])} ({_when(best_g)})"

            # Net vs Par (lowest is best)
            best_n = pdata.loc[pdata['NetVP'].idxmin()]
            row['Net'] = f"{_format_vs_par(best_n['NetVP'])} ({_when(best_n)})"

            # Stableford (highest is best)
            best_s = pdata.loc[pdata['Stableford'].idxmax()]
            row['Stfd'] = f"{int(best_s['Stableford'])} ({_when(best_s)})"

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
        sections = [{"title": title, "table_html": _df_to_html(display, cell_classes=cell_classes)}]
        return {"sections": sections}
    except Exception as e:
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
        return {"error": str(e)}


@router.get("/personal-bests")
async def personal_bests_page(request: Request):
    default_tab = "pb_summary"
    default_measure = "GrossVP"
    default_n = 1
    default_view = "rounds"

    if default_tab == "pb_summary":
        ctx = _pb_summary_context(default_view)
    else:
        ctx = _pb_tab_context(default_tab, default_measure, default_n)

    return templates.TemplateResponse("personal_bests.html", {
        "request": request,
        "active_page": "personal-bests",
        "tabs": PB_TABS,
        "active_tab": default_tab,
        "measures": PB_MEASURES,
        "selected_measure": default_measure,
        "n_records": default_n,
        "summary_views": PB_SUMMARY_VIEWS,
        "selected_view": default_view,
        **ctx,
    })


@router.get("/personal-bests/tab")
async def personal_bests_tab(
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
