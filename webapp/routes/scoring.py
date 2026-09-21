"""Scoring section routes: /scoring/*."""

import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.core.players import get_name_to_code
from teg_analysis.analysis.scoring import (
    calculate_par_performance_matrix,
    format_par_performance_table,
    count_scores_by_player,
    prepare_score_count_display,
    prepare_achievement_table_data,
    get_scoring_achievement_fields,
    format_vs_par,
)
from teg_analysis.analysis.streaks import (
    prepare_good_streaks_data, prepare_bad_streaks_data,
    prepare_current_good_streaks_data, prepare_current_bad_streaks_data,
    prepare_record_best_streaks_data, prepare_record_worst_streaks_data,
    calculate_window_streaks,
)
from teg_analysis.analysis.aggregation import (
    aggregate_data,
    get_round_data,
    calculate_final_round_differentials,
    calculate_biggest_leads_lost_after_r3,
    calculate_biggest_leads_lost_in_r4,
    calculate_biggest_comebacks,
)
from teg_analysis.io.file_operations import read_file
from teg_analysis.constants import ROUND_INFO_CSV
from teg_analysis.display.tables import score_type_stats, max_scoretype_per_round, max_scoretype_per_teg
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_ranked_round_data,
    cached_streaks_data,
    get_available_teg_numbers,
    get_default_teg_num,
    get_rounds_for_teg,
    parse_teg_label,
)
from webapp.chart_utils import get_chart_style, format_value, CROWDED_FIELD_THRESHOLD
from webapp.tables import df_to_html as _df_to_html, EMPTY_TABLE_HTML

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# --- /scoring/birdies ---------------------------------------------------------

BIRDIES_SCORE_TYPES = [
    ("Eagles", "Eagles"),
    ("Birdies", "Birdies"),
    ("Pars or Better", "Pars_or_Better"),
    ("TBP+", "TBPs"),
]

# Map display label → field name used in get_scoring_achievement_fields()
_BIRDIES_LABEL_TO_FIELD = {label: field for label, field in BIRDIES_SCORE_TYPES}

BIRDIES_TABS = [
    ("career", "Career Totals"),
    ("per_round", "Max per Round"),
    ("per_teg", "Max per TEG"),
]


def _birdies_tab_context(tab: str, score_type: str = "Birdies") -> dict:
    try:
        sections = []
        all_data = cached_load_all_data()

        # Resolve display label to field name
        field_name = _BIRDIES_LABEL_TO_FIELD.get(score_type, score_type)

        if tab == "career":
            stats = score_type_stats(all_data)
            if stats is not None and not stats.empty:
                # Filter to relevant columns for the chosen score type
                fields = get_scoring_achievement_fields()
                field_pair = None
                for fp in fields:
                    if fp[0] == field_name:
                        field_pair = fp
                        break
                if field_pair:
                    table = prepare_achievement_table_data(stats, field_pair)
                    sections.append({"title": f"{score_type} — Career", "table_html": _df_to_html(table)})
                else:
                    sections.append({"title": score_type, "table_html": _df_to_html(stats)})
            else:
                sections.append({"title": score_type, "table_html": "<p class='text-muted text-sm'>No data.</p>"})

        elif tab == "per_round":
            table = max_scoretype_per_round(all_data)
            sections.append({"title": f"Max {score_type} per Round", "table_html": _df_to_html(table)})

        elif tab == "per_teg":
            table = max_scoretype_per_teg(all_data)
            sections.append({"title": f"Max {score_type} per TEG", "table_html": _df_to_html(table)})

        return {"sections": sections}
    except Exception as e:
        logger.exception("_birdies_tab_context failed")
        return {"error": str(e)}


@router.get("/scoring/birdies")
def scoring_birdies_page(
    request: Request,
    tab: str = Query("career"),
    score_type: str = Query("Birdies"),
):
    tab = tab if tab in {tab_id for tab_id, _label in BIRDIES_TABS} else "career"
    score_type = score_type if score_type in _BIRDIES_LABEL_TO_FIELD else "Birdies"
    ctx = _birdies_tab_context(tab, score_type)
    return templates.TemplateResponse("scoring_birdies.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": BIRDIES_TABS,
        "active_tab": tab,
        "score_type": score_type,
        "score_types": [label for label, _ in BIRDIES_SCORE_TYPES],
        **ctx,
    })


@router.get("/scoring/birdies/tab")
def scoring_birdies_tab(request: Request, tab: str = Query("career"), score_type: str = Query("Birdies")):
    ctx = _birdies_tab_context(tab, score_type)
    return templates.TemplateResponse("partials/scoring_birdies_tab.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/streaks ---------------------------------------------------------

STREAK_TABS = [
    ("player", "Streaks by Player"),
    ("records", "Record Streaks"),
    ("detail", "Streak detail"),
]


def _streak_detail_context(d_teg: str = "All", d_round: str = "All", d_player: str = "All") -> dict:
    """Build the 'Streak detail' tab: filtered window-streak analysis."""
    all_data = cached_load_all_data()
    streaks_df = cached_streaks_data()
    df = streaks_df.merge(
        all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
        on=['HoleID', 'Pl'],
    ).sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])

    teg_options = ['All'] + sorted(df['TEG'].unique(), key=parse_teg_label)
    player_options = ['All'] + sorted(df['Pl'].unique().tolist())

    round_df = df if d_teg == 'All' else df[df['TEG'] == d_teg]
    round_options = ['All'] + sorted(round_df['Round'].unique().tolist())
    if d_round != 'All' and (round_df.empty or int(d_round) not in round_df['Round'].unique()):
        d_round = 'All'

    filtered = df.copy()
    if d_teg != 'All':
        filtered = filtered[filtered['TEG'] == d_teg]
    if d_round != 'All':
        filtered = filtered[filtered['Round'] == int(d_round)]
    if d_player != 'All':
        filtered = filtered[filtered['Pl'] == d_player]

    if filtered.empty:
        table_html = "<p class='text-muted text-sm'>No data matches the selected filters.</p>"
    else:
        results = calculate_window_streaks(filtered)
        table_html = _df_to_html(results) if results is not None and not results.empty \
            else "<p class='text-muted text-sm'>No streak data available for the selected filters.</p>"

    return {
        "detail": True,
        "table_html": table_html,
        "teg_options": teg_options,
        "round_options": round_options,
        "player_options": player_options,
        "d_teg": d_teg,
        "d_round": d_round,
        "d_player": d_player,
        "hole_count": int(len(filtered)),
    }


def _streak_tab_context(tab: str, direction: str = "good", mode: str = "max",
                        d_teg: str = "All", d_round: str = "All", d_player: str = "All") -> dict:
    """Build sections list for a given streaks tab."""
    try:
        if tab == "detail":
            return _streak_detail_context(d_teg, d_round, d_player)

        all_data = cached_load_all_data()
        sections = []
        caption = None

        if tab == "player":
            if mode == "max" and direction == "good":
                df = prepare_good_streaks_data(all_data)
                title = "Best Streaks (All-time Max)"
            elif mode == "max" and direction == "bad":
                df = prepare_bad_streaks_data(all_data)
                title = "Worst Streaks (All-time Max)"
            elif mode == "current" and direction == "good":
                df = prepare_current_good_streaks_data(all_data)
                title = "Current Good Streaks"
            else:
                df = prepare_current_bad_streaks_data(all_data)
                title = "Current Bad Streaks"
            sections.append({"title": title, "table_html": _df_to_html(df)})

        elif tab == "records":
            best = prepare_record_best_streaks_data(all_data)
            worst = prepare_record_worst_streaks_data(all_data)
            sections.append({"title": "Record Best Streaks", "table_html": _df_to_html(best)})
            sections.append({"title": "Record Worst Streaks", "table_html": _df_to_html(worst)})
            caption = "*: current streak is record streak"

        return {"sections": sections, "caption": caption}
    except Exception as e:
        logger.exception("_streak_tab_context failed")
        return {"error": str(e)}


@router.get("/scoring/streaks")
def scoring_streaks_page(
    request: Request,
    tab: str = Query("player"),
    direction: str = Query("good"),
    mode: str = Query("max"),
    d_teg: str = Query("All"),
    d_round: str = Query("All"),
    d_player: str = Query("All"),
):
    tab = tab if tab in {tab_id for tab_id, _label in STREAK_TABS} else "player"
    direction = direction if direction in {"good", "bad"} else "good"
    mode = mode if mode in {"max", "current"} else "max"
    d_round = d_round if d_round == "All" or d_round.isdigit() else "All"
    ctx = _streak_tab_context(tab, direction, mode, d_teg, d_round, d_player)
    return templates.TemplateResponse("scoring_streaks.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": STREAK_TABS,
        "active_tab": tab,
        "direction": direction,
        "mode": mode,
        **ctx,
    })


@router.get("/scoring/streaks/tab")
def scoring_streaks_tab(
    request: Request,
    tab: str = Query("player"),
    direction: str = Query("good"),
    mode: str = Query("max"),
    d_teg: str = Query("All"),
    d_round: str = Query("All"),
    d_player: str = Query("All"),
):
    ctx = _streak_tab_context(tab, direction, mode, d_teg, d_round, d_player)
    return templates.TemplateResponse("partials/scoring_streaks_tab.html", {
        "request": request,
        "tab": tab,
        **ctx,
    })


# --- /scoring/by-par ----------------------------------------------------------

def _by_par_context(teg: int = 0) -> dict:
    """Build table_html for the by-par page, optionally filtered to a single TEG."""
    try:
        all_data = cached_load_all_data()
        if teg > 0:
            all_data = all_data[all_data['TEGNum'] == teg]
        matrix = calculate_par_performance_matrix(all_data)
        formatted = format_par_performance_table(matrix)
        # Player column crowds the four numeric columns at 320-390px (see
        # .by-par-panel in mobile.css) -- shorten to Initial.SURNAME there.
        return {"table_html": _df_to_html(formatted, shorten_players=True)}
    except Exception as e:
        logger.exception("_by_par_context failed")
        return {"error": str(e)}


@router.get("/scoring/by-par")
def scoring_by_par_page(request: Request, teg: int = Query(0)):
    ctx = _by_par_context(teg)
    teg_numbers = get_available_teg_numbers()
    return templates.TemplateResponse("scoring_by_par.html", {
        "request": request,
        "active_page": "scoring",
        "teg_numbers": teg_numbers,
        "selected_teg": teg,
        **ctx,
    })


@router.get("/scoring/by-par/content")
def scoring_by_par_content(request: Request, teg: int = Query(0)):
    ctx = _by_par_context(teg)
    return templates.TemplateResponse("partials/scoring_matrix_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/by-teg ----------------------------------------------------------

def _by_teg_chart(agg: pd.DataFrame) -> tuple[str, list]:
    """Build a Plotly line chart of GrossVP by TEG per player, return
    (figure JSON, below-chart readout). The readout mirrors each line's
    final value/colour (see get_teg_chart_readout in chart_utils.py) so the
    phone-only chart treatment (base.html::applyMobileChartTreatment, opted
    into via the .chart-block wrapper in scoring_by_teg.html) can hide the
    native legend without losing player identity -- colours are assigned
    explicitly here, in the same order/palette Plotly's default colorway
    would already pick, so the desktop/iPad figure is unchanged."""
    import plotly.graph_objects as go
    import plotly.express as px

    players = sorted(agg['Player'].unique())
    palette = px.colors.qualitative.Plotly
    color_map = {p: palette[i % len(palette)] for i, p in enumerate(players)}
    name_to_code = get_name_to_code()

    fig = go.Figure()
    readout = []
    for player in players:
        pdata = agg[agg['Player'] == player].sort_values('TEGNum')
        color = color_map[player]
        fig.add_trace(go.Scatter(
            x=pdata['TEGNum'], y=pdata['GrossVP'],
            mode='lines+markers', name=player,
            line=dict(width=2, color=color), marker=dict(size=4, color=color),
        ))
        readout.append({
            "code": name_to_code.get(player, player),
            "name": player,
            "value": format_value(pdata['GrossVP'].iloc[-1], 'gross'),
            "color": color,
        })

    fig.update_layout(
        xaxis_title='TEG', yaxis_title='Avg Gross vs Par',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(r=20, t=10, b=40, l=50),
        font=dict(family="monospace"),
    )
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    fig.update_layout(**get_chart_style('streamlit'))

    return fig.to_json(), readout


@router.get("/scoring/by-teg")
def scoring_by_teg_page(request: Request):
    chart_json = None
    chart_readout = []
    try:
        all_data = cached_load_all_data()
        agg = aggregate_data(all_data, 'TEG', measures=['GrossVP'])
        # Pivot on 'Pl' (initials) rather than 'Player' (full name) for header
        # columns; the chart above keeps 'Player' for legend legibility.
        pivot = agg.pivot_table(index='TEGNum', columns='Pl', values='GrossVP', aggfunc='first')
        player_cols = list(pivot.columns)
        pivot = pivot.reset_index()

        # GrossVP per TEG is a sum of whole-number per-round vs-par values,
        # so it is always a whole number in practice (verified against real
        # data: 0 fractional values across all TEG/player combinations).
        # Format defensively anyway: whole numbers with no decimal, any
        # genuinely fractional value to 1dp.
        def _fmt_cell(v):
            if pd.isna(v):
                return ''
            return f"{int(v)}" if float(v) == int(v) else f"{v:.1f}"

        for c in player_cols:
            pivot[c] = pivot[c].apply(_fmt_cell)
        pivot['TEGNum'] = pivot['TEGNum'].astype(int).astype(str)
        pivot = pivot.rename(columns={'TEGNum': 'TEG'})
        table_html = _df_to_html(pivot)
        chart_json, chart_readout = _by_teg_chart(agg)
    except Exception as e:
        logger.exception("scoring_by_teg_page failed")
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("scoring_by_teg.html", {
        "request": request,
        "active_page": "scoring",
        "table_html": table_html,
        "chart_json": chart_json,
        "chart_readout": chart_readout,
        "chart_crowded_threshold": CROWDED_FIELD_THRESHOLD,
    })


# --- /scoring/by-course -------------------------------------------------------

COURSE_TABS = [
    ("gross_records", "Gross Records"),
    ("net_records", "Net Records"),
    ("summary", "Summary"),
    ("averages", "Averages"),
    ("bests", "Bests"),
    ("worsts", "Worsts"),
]


def _format_vp(val, decimals=0):
    """Format a vs-par value: +N, -N, or = for zero."""
    if pd.isna(val):
        return "-"
    if val == 0:
        return "="
    if decimals == 0:
        return f"{int(val):+d}"
    return f"{val:+.{decimals}f}"


def _two_line_cell_table_html(df: pd.DataFrame, composite_col: str, table_class: str = "teg-table") -> str:
    """Render a table where one column holds a "value (context)" composite
    string (e.g. "75 (+4)"), splitting it into two text-node spans.

    Mirrors _pb_summary_html's exact mechanism (webapp/routes/performance.py,
    the PB Summary table): the " (" / ")" separators are plain text nodes,
    not CSS-generated content, so with no CSS at all (desktop/iPad, which
    get no rules outside mobile.css's @media block) the cell reads exactly
    as the old concatenated string. mobile.css's .course-records-page rules
    stack the value/context spans into two centered lines and hide the
    separators below 640px.
    """
    if df is None or df.empty:
        return EMPTY_TABLE_HTML
    cols = list(df.columns)
    rows = [f"<table class='{table_class}'><thead><tr>"]
    for col in cols:
        rows.append(f"<th>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in cols:
            val = row[col]
            if col == composite_col and isinstance(val, str) and val.endswith(')') and ' (' in val:
                value_str, _, context_str = val.partition(' (')
                context_str = context_str[:-1]
                rows.append(
                    f"<td><span class='cr-v'>{escape(value_str)}</span>"
                    f"<span class='cr-sep'> (</span>"
                    f"<span class='cr-c'>{escape(context_str)}</span>"
                    f"<span class='cr-sep'>)</span></td>"
                )
            else:
                rows.append(f"<td>{escape(str(val))}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _get_course_areas():
    """Return list of area filter options from round_info."""
    try:
        round_info = read_file(ROUND_INFO_CSV)
        areas = sorted(round_info['Area'].dropna().unique().tolist())
        return ["All Areas"] + areas
    except Exception:
        return ["All Areas"]


def _filter_by_area(rd_data: pd.DataFrame, area: str) -> pd.DataFrame:
    """Filter round data by area. Returns unfiltered if 'All Areas'."""
    if area == "All Areas" or not area:
        return rd_data
    if 'Area' in rd_data.columns:
        return rd_data[rd_data['Area'] == area]
    return rd_data


def _course_tab_context(tab: str, area: str = "All Areas") -> dict:
    """Build sections list for a given course-analysis tab."""
    try:
        rd_data = cached_round_data()
        rd_data = _filter_by_area(rd_data, area)

        if rd_data.empty or 'Course' not in rd_data.columns:
            return {"sections": []}

        sections = []

        if tab == "gross_records":
            # Best gross round per course (by raw score Sc)
            records = []
            for course in rd_data['Course'].unique():
                cd = rd_data[rd_data['Course'] == course]
                min_sc = cd['Sc'].min()
                best = cd[cd['Sc'] == min_sc]
                for _, r in best.iterrows():
                    teg_round = f"{r.get('TEG', '')} R{int(r['Round'])}" if 'TEG' in r.index else f"TEG {r['TEGNum']} R{int(r['Round'])}"
                    records.append({
                        'Course': course,
                        'Score': f"{int(r['Sc'])} ({_format_vp(r['GrossVP'])})",
                        'Player': r['Player'],
                        'Date': r.get('Date', ''),
                        'TEG / Round': teg_round,
                    })
            if records:
                df = pd.DataFrame(records)
                df['_sort'] = df['Score'].str.extract(r'(\d+)').astype(int)
                df = df.sort_values('_sort').drop(columns='_sort')
                sections.append({
                    "title": "Course Records (Gross)",
                    "table_html": _two_line_cell_table_html(df, "Score", "teg-table cr-records-table"),
                })

                # Summary: records held per player
                holder_counts = df.groupby('Player')['Course'].nunique().reset_index()
                holder_counts.columns = ['Player', 'Records Held']
                holder_counts = holder_counts.sort_values('Records Held', ascending=False)
                sections.append({"title": "Records by Player", "table_html": _df_to_html(holder_counts)})

        elif tab == "net_records":
            records = []
            for course in rd_data['Course'].unique():
                cd = rd_data[rd_data['Course'] == course]
                min_net = cd['NetVP'].min()
                best = cd[cd['NetVP'] == min_net]
                for _, r in best.iterrows():
                    teg_round = f"{r.get('TEG', '')} R{int(r['Round'])}" if 'TEG' in r.index else f"TEG {r['TEGNum']} R{int(r['Round'])}"
                    records.append({
                        'Course': course,
                        'Net vs Par': _format_vp(r['NetVP']),
                        'Player': r['Player'],
                        'Date': r.get('Date', ''),
                        'TEG / Round': teg_round,
                    })
            if records:
                df = pd.DataFrame(records)
                df['_sort'] = df['Net vs Par'].str.replace('+', '').str.replace('=', '0').astype(int)
                df = df.sort_values('_sort').drop(columns='_sort')
                sections.append({"title": "Course Records (Net)", "table_html": _df_to_html(df)})

                holder_counts = df.groupby('Player')['Course'].nunique().reset_index()
                holder_counts.columns = ['Player', 'Net Records Held']
                holder_counts = holder_counts.sort_values('Net Records Held', ascending=False)
                sections.append({"title": "Net Records by Player", "table_html": _df_to_html(holder_counts)})

        elif tab == "summary":
            summary = rd_data.groupby('Course').agg(
                Rounds=('GrossVP', 'count'),
                BestGross=('GrossVP', 'min'),
                AvgGross=('GrossVP', 'mean'),
                WorstGross=('GrossVP', 'max'),
                BestNet=('NetVP', 'min'),
                AvgNet=('NetVP', 'mean'),
                WorstNet=('NetVP', 'max'),
            ).reset_index().sort_values('Rounds', ascending=False)

            # Format columns
            for col in ['BestGross', 'WorstGross', 'BestNet', 'WorstNet']:
                summary[col] = summary[col].apply(lambda v: _format_vp(v, 0))
            for col in ['AvgGross', 'AvgNet']:
                summary[col] = summary[col].apply(lambda v: _format_vp(v, 1))
            summary['Rounds'] = summary['Rounds'].astype(int)

            summary.columns = ['Course', 'Rounds', 'Best Gross', 'Avg Gross', 'Worst Gross', 'Best Net', 'Avg Net', 'Worst Net']
            sections.append({"title": "Summary by Course", "table_html": _df_to_html(summary)})

        elif tab == "averages":
            # Pivot on 'Pl' (initials) -- same dense metric-grid treatment as
            # Matrix/By TEG; the Course column wraps to two lines instead of
            # needing to fit a full course name on one, freeing width for
            # the 7 initials + Total columns (mobile.css).
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc='mean')
            # Add Total column
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].mean()
            pivot = pivot.round(1).reset_index()
            pivot.columns.name = None
            # Format numeric cells
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 1))
            sections.append({"title": "Average Gross vs Par by Course", "table_html": _df_to_html(pivot, table_class="teg-table cr-matrix-table")})

        elif tab == "bests":
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc='min')
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].min()
            pivot = pivot.reset_index()
            pivot.columns.name = None
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 0))
            sections.append({"title": "Best Gross vs Par by Course", "table_html": _df_to_html(pivot, table_class="teg-table cr-matrix-table")})

        elif tab == "worsts":
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Pl', aggfunc='max')
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].max()
            pivot = pivot.reset_index()
            pivot.columns.name = None
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 0))
            sections.append({"title": "Worst Gross vs Par by Course", "table_html": _df_to_html(pivot, table_class="teg-table cr-matrix-table")})

        return {"sections": sections}
    except Exception as e:
        logger.exception("_course_tab_context failed")
        return {"error": str(e)}


@router.get("/scoring/by-course")
def scoring_by_course_page(
    request: Request,
    tab: str = Query("gross_records"),
    area: str = Query("All Areas"),
):
    areas = _get_course_areas()
    tab = tab if tab in {tab_id for tab_id, _label in COURSE_TABS} else "gross_records"
    area = area if area in areas else "All Areas"
    ctx = _course_tab_context(tab, area)
    return templates.TemplateResponse("scoring_by_course.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": COURSE_TABS,
        "active_tab": tab,
        "areas": areas,
        "selected_area": area,
        **ctx,
    })


@router.get("/scoring/by-course/tab")
def scoring_by_course_tab(request: Request, tab: str = Query("gross_records"), area: str = Query("All Areas")):
    ctx = _course_tab_context(tab, area)
    return templates.TemplateResponse("partials/scoring_by_course_tab.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/all-rounds ------------------------------------------------------

ALL_ROUNDS_MEASURES = [
    ("Sc", "Score"),
    ("GrossVP", "Gross vs Par"),
    ("Stableford", "Stableford"),
    ("NetVP", "Net vs Par"),
]


def _build_all_rounds_byline_html(out: pd.DataFrame, friendly: str) -> str:
    """Mobile-only byline-row list for All Rounds.

    'Player' is already the full name (no naming-rule change needed here).
    Primary line is Player + the selected measure value; the rest
    (Course, TEG-Round, Year, PB Rank) demote to one muted sub-line.
    """
    if out is None or out.empty:
        return ""
    name_to_code = get_name_to_code()
    rows_html = []
    for _, row in out.iterrows():
        player_html = _player_link_html(row['Player'], name_to_code)
        primary = (
            f'<span class="bl-player">{player_html}</span>'
            f'<span class="bl-value">{escape(str(row[friendly]))}</span>'
        )
        sub = f'{row["Course"]} · {row["TEG-Round"]} · {int(row["Year"])} · PB {row["PB Rank"]}'
        rows_html.append(_byline_row_html(primary, sub, "ar-row"))
    return _byline_list_html(rows_html, "ar-list")


def _all_rounds_context(area: str, course: str, player: str, measure: str, n: int) -> dict:
    try:
        rd = cached_ranked_round_data().copy()
        rd['Pl_count'] = rd.groupby('Pl')['Pl'].transform('count')

        rd = _filter_by_area(rd, area)
        courses = ["All courses"] + sorted(rd['Course'].dropna().unique().tolist())
        if course != "All courses":
            rd = rd[rd['Course'] == course]
        players = ["All players"] + sorted(rd['Player'].dropna().unique().tolist())
        if player != "All players":
            rd = rd[rd['Player'] == player]

        if measure not in rd.columns:
            measure = "GrossVP"
        friendly = dict(ALL_ROUNDS_MEASURES).get(measure, measure)
        ascending = measure != "Stableford"
        rd = rd.sort_values(by=measure, ascending=ascending)

        pl_rank_col = f"Rank_within_player_{measure}"
        out = rd[['Player', 'Course', measure, 'TEG-Round', 'Year', pl_rank_col, 'Pl_count']].copy()
        out = out.rename(columns={measure: friendly, pl_rank_col: 'PB Rank'})
        out['PB Rank'] = out['PB Rank'].astype(int).astype(str) + '/' + out['Pl_count'].astype(int).astype(str)
        out = out.drop(columns='Pl_count')
        out[friendly] = out[friendly].astype(int)
        out['Year'] = out['Year'].astype(int)
        out = out.head(n)

        title = f"All rounds for {player} at {course}"
        return {
            "table_html": _df_to_html(out) + _build_all_rounds_byline_html(out, friendly),
            "result_title": title,
            "areas": _get_course_areas(),
            "measures": ALL_ROUNDS_MEASURES,
            "courses": courses,
            "players": players,
            "selected_area": area,
            "selected_course": course,
            "selected_player": player,
            "selected_measure": measure,
            "n_records": n,
        }
    except Exception as e:
        logger.exception("_all_rounds_context failed")
        return {"error": str(e)}


@router.get("/scoring/all-rounds")
def scoring_all_rounds_page(
    request: Request,
    area: str = Query("All Areas"),
    course: str = Query("All courses"),
    player: str = Query("All players"),
    measure: str = Query("GrossVP"),
    n: int = Query(10),
):
    ctx = _all_rounds_context(area, course, player, measure, n)
    return templates.TemplateResponse("scoring_all_rounds.html", {
        "request": request,
        "active_page": "scoring",
        **ctx,
    })


@router.get("/scoring/all-rounds/content")
def scoring_all_rounds_content(
    request: Request,
    area: str = Query("All Areas"),
    course: str = Query("All courses"),
    player: str = Query("All players"),
    measure: str = Query("GrossVP"),
    n: int = Query(10),
):
    ctx = _all_rounds_context(area, course, player, measure, n)
    return templates.TemplateResponse("partials/scoring_all_rounds_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/matrix ----------------------------------------------------------

MATRIX_LEVELS = [("teg", "By TEG"), ("round", "By Round"), ("9", "By 9")]
MATRIX_TYPES = [("GrossVP", "Gross vs Par"), ("Stableford", "Stableford"), ("Sc", "Score"), ("NetVP", "Net vs Par")]


def _matrix_context(level: str = "teg", score_type: str = "GrossVP") -> dict:
    try:
        if level == "9":
            from webapp.deps import cached_9_data
            data = cached_9_data()
            idx_cols = ['TEGNum', 'Round', 'FrontBack']
        elif level == "round":
            data = cached_round_data()
            idx_cols = ['TEGNum', 'Round']
        else:
            from webapp.deps import cached_complete_teg_data
            data = cached_complete_teg_data()
            idx_cols = ['TEGNum']

        if score_type not in data.columns:
            return {"error": f"Column {score_type} not found"}

        # Use Pl (initials) as column names if available
        player_col = 'Pl' if 'Pl' in data.columns else 'Player'

        pivot = data.pivot_table(index=idx_cols, columns=player_col, values=score_type, aggfunc='first')

        # Add Average column (numeric, before formatting)
        avg = pivot.mean(axis=1)

        is_vp = score_type in ('GrossVP', 'NetVP')
        player_cols = list(pivot.columns)

        pivot = pivot.reset_index()
        pivot['Average'] = avg.values

        if is_vp:
            # vs-par columns get signed integers; Average signed to 1 dp
            for c in player_cols:
                pivot[c] = pivot[c].apply(lambda v: format_vs_par(round(v)) if pd.notna(v) else '')
            pivot['Average'] = pivot['Average'].apply(lambda v: f"{v:+.1f}" if pd.notna(v) else '')
        else:
            # Score / Stableford: integer player values, 1 dp Average
            for c in player_cols:
                pivot[c] = pivot[c].apply(lambda v: f"{int(round(v))}" if pd.notna(v) else '')
            pivot['Average'] = pivot['Average'].apply(lambda v: f"{v:.1f}" if pd.notna(v) else '')

        if 'TEGNum' in pivot.columns:
            pivot = pivot.rename(columns={'TEGNum': 'TEG'})
        table_html = _df_to_html(pivot)
        return {"table_html": table_html}
    except Exception as e:
        logger.exception("_matrix_context failed")
        return {"error": str(e)}


@router.get("/scoring/matrix")
def scoring_matrix_page(
    request: Request,
    level: str = Query("teg"),
    score_type: str = Query("GrossVP"),
):
    level = level if level in {level_id for level_id, _label in MATRIX_LEVELS} else "teg"
    score_type = score_type if score_type in {type_id for type_id, _label in MATRIX_TYPES} else "GrossVP"
    ctx = _matrix_context(level, score_type)
    return templates.TemplateResponse("scoring_matrix.html", {
        "request": request,
        "active_page": "scoring",
        "wide": True,
        "levels": MATRIX_LEVELS,
        "score_types": MATRIX_TYPES,
        "selected_level": level,
        "selected_type": score_type,
        **ctx,
    })


@router.get("/scoring/matrix/content")
def scoring_matrix_content(request: Request, level: str = Query("teg"), score_type: str = Query("GrossVP")):
    ctx = _matrix_context(level, score_type)
    return templates.TemplateResponse("partials/scoring_matrix_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/distributions ---------------------------------------------------

def _distributions_chart(display: pd.DataFrame, is_pct: bool = False,
                          all_players_pct: list | None = None) -> tuple[str | None, list]:
    """Build a grouped bar chart of score distributions by player, return
    (figure JSON, below-chart readout). ``display``'s player columns are
    already codes (count_scores_by_player unstacks on 'Pl'), so the readout's
    data-chart-focus values match each bar trace's name directly -- see
    _by_teg_chart for the equivalent full-name case. Colours are assigned
    explicitly, in the order/palette Plotly's default colorway already picks
    for these traces, so the desktop/iPad figure is unchanged.

    In percentage mode (``is_pct``), ``display`` holds per-player percentages
    and ``all_players_pct`` (aligned to ``display``'s rows) is overlaid as an
    "All players" tick per score category rather than another bar.
    """
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        from teg_analysis.core.players import get_player_name

        if display is None or display.empty:
            return None, []

        # First column is the score label, rest are players
        score_col = display.columns[0]
        player_cols = [c for c in display.columns[1:] if c not in ('Total',)]
        palette = px.colors.qualitative.Plotly
        color_map = {p: palette[i % len(palette)] for i, p in enumerate(player_cols)}

        fig = go.Figure()
        readout = []
        for player in player_cols:
            y_values = pd.to_numeric(display[player], errors='coerce')
            color = color_map[player]
            fig.add_trace(go.Bar(
                x=display[score_col],
                y=y_values,
                name=player,
                marker=dict(color=color),
            ))
            # No single "final value" makes sense for a distribution bar
            # chart (a percentage-mode total is always ~100%; a count-mode
            # total is just games played, not a distribution stat) -- this
            # readout exists purely to keep player identity/colour visible
            # once the native legend is hidden on phones, not to add a stat.
            readout.append({
                "code": player,
                "name": get_player_name(player),
                "value": "",
                "color": color,
            })

        if is_pct and all_players_pct is not None:
            fig.add_trace(go.Scatter(
                x=display[score_col],
                y=all_players_pct,
                mode='markers',
                marker=dict(symbol='line-ew-open', size=26, line=dict(width=2)),
                name='All players',
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Score vs Par',
            yaxis_title='% of holes' if is_pct else 'Count',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(r=20, t=10, b=40, l=50),
            font=dict(family="monospace"),
        )
        fig.layout.xaxis.fixedrange = True
        fig.layout.yaxis.fixedrange = True
        fig.update_layout(**get_chart_style('streamlit'))

        return fig.to_json(), readout
    except Exception:
        return None, []


def _all_players_score_pct(filtered: pd.DataFrame, field: str, index) -> list:
    """Combined score distribution across all players (as % of all holes in
    ``filtered``), aligned row-for-row to ``index`` (a count-data index of raw
    score-field values, e.g. count_data.index before display formatting)."""
    counts = filtered.groupby(field).size()
    total = counts.sum()
    if not total:
        return [0.0] * len(index)
    pct = (counts / total * 100).round(1)
    return [float(pct.get(v, 0.0)) for v in index]


DIST_FIELDS = [("Sc", "Scores"), ("GrossVP", "Scores vs Par"), ("Stableford", "Stableford Points")]
_DIST_DISPLAY_NAME = {"Sc": "Score", "GrossVP": "vs Par", "Stableford": "Stableford"}
DIST_TABS = [("player", "By Player"), ("teg", "By TEG")]


def _distributions_context(field="Stableford", player="All players", teg="All TEGs",
                           par="All pars", mode="Percentage", tab="player") -> dict:
    try:
        all_data = cached_load_all_data()
        if field not in ("Sc", "GrossVP", "Stableford"):
            field = "Stableford"
        display_name = _DIST_DISPLAY_NAME[field]
        is_pct = mode == "Percentage"

        player_options = ["All players"] + sorted(all_data["Pl"].unique().tolist())
        teg_options = ["All TEGs"] + [str(t) for t in sorted(all_data["TEGNum"].unique().tolist(), reverse=True)]
        par_options = ["All pars", "Par 3", "Par 4", "Par 5"]

        # Apply TEG + par filters
        filtered = all_data
        if teg != "All TEGs":
            filtered = filtered[filtered["TEGNum"] == int(teg)]
        if par != "All pars":
            filtered = filtered[filtered["PAR"] == int(par.replace("Par ", ""))]
        player_filtered = filtered if player == "All players" else filtered[filtered["Pl"] == player]

        chart_json = None
        chart_readout = []
        if tab == "player":
            count_data = count_scores_by_player(player_filtered, field)
            if is_pct:
                totals = count_data.sum(axis=0).replace(0, pd.NA)
                display_data = (count_data.div(totals, axis=1) * 100).round(1)
            else:
                display_data = count_data
            table = prepare_score_count_display(display_data, field, display_name, is_pct)
            table_html = _df_to_html(table)
            if is_pct:
                chart_table = prepare_score_count_display(display_data, field, display_name, False)
                all_players_pct = _all_players_score_pct(filtered, field, count_data.index)
            else:
                chart_table = prepare_score_count_display(count_data, field, display_name, False)
                all_players_pct = None
            chart_json, chart_readout = _distributions_chart(chart_table, is_pct, all_players_pct)
        else:
            # By TEG crosstab (respects par + player filters, not TEG)
            teg_filtered = all_data
            if par != "All pars":
                teg_filtered = teg_filtered[teg_filtered["PAR"] == int(par.replace("Par ", ""))]
            if player != "All players":
                teg_filtered = teg_filtered[teg_filtered["Pl"] == player]
            if is_pct:
                crosstab = pd.crosstab(teg_filtered["TEGNum"], teg_filtered[field], normalize="index") * 100
                crosstab = crosstab.round(1)
            else:
                crosstab = pd.crosstab(teg_filtered["TEGNum"], teg_filtered[field])
            ct = crosstab.reset_index()
            ct.columns.name = None
            if field == "GrossVP":
                ct = ct.rename(columns={c: (format_vs_par(c) if c != "TEGNum" else c) for c in ct.columns})
            for col in ct.columns:
                if col == "TEGNum":
                    continue
                if is_pct:
                    ct[col] = ct[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")
                else:
                    ct[col] = ct[col].apply(lambda x: int(x) if pd.notna(x) else 0)
            ct = ct.rename(columns={"TEGNum": "TEG"})
            table_html = _df_to_html(ct)

        return {
            "table_html": table_html,
            "chart_json": chart_json,
            "chart_readout": chart_readout,
            "chart_crowded_threshold": CROWDED_FIELD_THRESHOLD,
            "fields": DIST_FIELDS,
            "player_options": player_options,
            "teg_options": teg_options,
            "par_options": par_options,
            "tabs": DIST_TABS,
            "selected_field": field,
            "selected_player": player,
            "selected_teg": teg,
            "selected_par": par,
            "mode": mode,
            "active_tab": tab,
        }
    except Exception as e:
        logger.exception("_distributions_context failed")
        return {"error": str(e)}


@router.get("/scoring/distributions")
def scoring_distributions_page(request: Request, field="Stableford", player="All players",
                                     teg="All TEGs", par="All pars", mode="Percentage", tab="player"):
    ctx = _distributions_context(field, player, teg, par, mode, tab)
    return templates.TemplateResponse("scoring_distributions.html", {
        "request": request,
        "active_page": "scoring",
        **ctx,
    })


@router.get("/scoring/distributions/content")
def scoring_distributions_content(request: Request, field="Stableford", player="All players",
                                        teg="All TEGs", par="All pars", mode="Percentage", tab="player"):
    ctx = _distributions_context(field, player, teg, par, mode, tab)
    return templates.TemplateResponse("partials/scoring_distributions_content.html", {
        "request": request,
        **ctx,
    })


# --- Byline-row helpers (mobile-only list, shared across Changes/Comebacks/
# All Rounds) -----------------------------------------------------------------
#
# Same dual-markup + CSS-toggle mechanism as Top Performances'
# .tp-table/.tp-list (see _build_top_performances_byline_html,
# webapp/routes/performance.py): the desktop <table> is untouched, and this
# renders an alongside phone-only list -- a primary line with the 2-3
# headline facts, and a muted secondary line with everything else joined by
# " · ". mobile.css hides one or the other per breakpoint.

def _player_link_html(name, name_to_code: dict) -> str:
    # Player profiles hidden 2026-09-18: pages not ready to be live, so this
    # renders plain text rather than a `/player/<code>` link.
    return escape(str(name))


def _byline_row_html(primary_html: str, sub_text: str, row_class: str) -> str:
    return (
        f'<div class="{row_class}"><div class="bl-top">{primary_html}</div>'
        f'<div class="bl-sub">{escape(sub_text)}</div></div>'
    )


def _byline_list_html(rows_html: list, list_class: str) -> str:
    if not rows_html:
        return ""
    return f'<div class="{list_class}">' + "".join(rows_html) + '</div>'


# --- /scoring/changes ---------------------------------------------------------

CHANGES_TABS = [("improvements", "Biggest improvements"), ("worsenings", "Biggest worsenings")]
_CHANGES_TOP_N = 10


def _build_changes_byline_html(out: pd.DataFrame) -> str:
    """Mobile-only byline-row list for Changes vs Previous Round.

    The desktop table gives 'Player' and five context columns (TEG, Round,
    Course, Year, Previous Rd) equal footing -- fine on a wide screen, but
    the player's full name plus all of that crowds a phone row. Leads with
    the two headline facts (Score, Change -- the "what changed" number) next
    to the full name, and demotes TEG/Round/Course/Year/Previous Rd onto one
    muted sub-line so nothing is dropped, just reordered by importance.
    """
    if out is None or out.empty:
        return ""
    name_to_code = get_name_to_code()
    rows_html = []
    for _, row in out.iterrows():
        player_html = _player_link_html(row['Player'], name_to_code)
        change_text = f"{int(row['Change']):+d}"
        primary = (
            f'<span class="bl-player">{player_html}</span>'
            f'<span class="bl-value">{escape(str(int(row["Sc"])))}</span>'
            f'<span class="bl-delta">{escape(change_text)}</span>'
        )
        sub = (
            f'{row["TEG"]} · Round {int(row["Round"])} · {row["Course"]} · '
            f'{int(row["Year"])} · Previous {int(row["Previous Rd"])}'
        )
        rows_html.append(_byline_row_html(primary, sub, "ch-row"))
    return _byline_list_html(rows_html, "ch-list")


def _changes_context(teg: str = "All TEGs", across: str = "within",
                     rows: str = "top", tab: str = "improvements") -> dict:
    try:
        rd = cached_round_data().copy()
        rd['TR'] = rd['TEGNum'] * 100 + rd['Round']

        teg_options = ["All TEGs"] + [str(t) for t in sorted(rd['TEGNum'].unique().tolist(), reverse=True)]
        if teg != "All TEGs":
            rd = rd[rd['TEGNum'] == int(teg)]

        grouper = ['Pl'] if across == "across" else ['Pl', 'TEG']
        rd = rd.sort_values(['Pl', 'TR'])
        rd['Change'] = rd.groupby(grouper)['Sc'].diff()
        rd['Previous Rd'] = rd.groupby(grouper)['Sc'].shift()
        rd = rd.dropna(subset=['Change'])

        if rd.empty:
            return {"table_html": "<p class='text-muted text-sm'>No data available.</p>",
                    "teg_options": teg_options, "selected_teg": teg, "across": across,
                    "rows": rows, "tabs": CHANGES_TABS, "active_tab": tab, "top_n": _CHANGES_TOP_N}

        rd[['Sc', 'Previous Rd', 'Change']] = rd[['Sc', 'Previous Rd', 'Change']].astype(int)
        out = rd[['Player', 'TEG', 'Round', 'Course', 'Year', 'Sc', 'Previous Rd', 'Change']].copy()
        out['Year'] = out['Year'].astype(int)

        if tab == "worsenings":
            out = out.sort_values('Change', ascending=False)
            if rows != "all":
                out = out.nlargest(_CHANGES_TOP_N, 'Change', keep='all')
        else:
            out = out.sort_values('Change', ascending=True)
            if rows != "all":
                out = out.nsmallest(_CHANGES_TOP_N, 'Change', keep='all')

        return {
            "table_html": _df_to_html(out) + _build_changes_byline_html(out),
            "teg_options": teg_options,
            "selected_teg": teg,
            "across": across,
            "rows": rows,
            "tabs": CHANGES_TABS,
            "active_tab": tab,
            "top_n": _CHANGES_TOP_N,
        }
    except Exception as e:
        logger.exception("_changes_context failed")
        return {"error": str(e)}


@router.get("/scoring/changes")
def scoring_changes_page(request: Request, teg: str = Query("All TEGs"),
                               across: str = Query("within"), rows: str = Query("top"),
                               tab: str = Query("improvements")):
    ctx = _changes_context(teg, across, rows, tab)
    return templates.TemplateResponse("scoring_changes.html", {
        "request": request,
        "active_page": "scoring",
        **ctx,
    })


@router.get("/scoring/changes/content")
def scoring_changes_content(request: Request, teg: str = Query("All TEGs"),
                                  across: str = Query("within"), rows: str = Query("top"),
                                  tab: str = Query("improvements")):
    ctx = _changes_context(teg, across, rows, tab)
    return templates.TemplateResponse("partials/scoring_changes_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/comebacks -------------------------------------------------------

_COMEBACK_SCORE_COLS = {
    "Final Round Score", "Total Score", "Gap Closed", "Lead Lost",
    "Lead", "Max Lead", "Comeback", "Differential", "Final Round Differential",
}


def _fmt_comebacks(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Format float columns: signed vs-par for gross score columns, ints elsewhere."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for c in out.columns:
        if out[c].dtype.kind == "f":
            if measure == "GrossVP" and c in _COMEBACK_SCORE_COLS:
                out[c] = out[c].apply(lambda v: format_vs_par(int(round(v))) if pd.notna(v) else "")
            else:
                out[c] = out[c].apply(lambda v: str(int(round(v))) if pd.notna(v) else "")
    return out


def _build_comebacks_byline_html(df: pd.DataFrame, id_col: str, headline_cols: list, context_cols: list) -> str:
    """Mobile-only byline-row list for one /scoring/comebacks section.

    The 6 sections on this page come from 4 different calculator functions
    (teg_analysis.analysis.aggregation) and each has its own column shape --
    e.g. the "Biggest Leads Lost..." tables identify the player via a
    'Leader After R3' column, not 'Player' -- so the headline/context split
    is passed in per call (see _comebacks_context) rather than assumed.
    Primary line: identity + whatever column(s) that section's title is
    actually about (its "headline" figure). Sub-line: everything else,
    joined with " · ", same as the other byline lists on this page.
    """
    if df is None or df.empty:
        return ""
    name_to_code = get_name_to_code()
    rows_html = []
    for _, row in df.iterrows():
        player_html = _player_link_html(row[id_col], name_to_code)
        # Label the headline figure(s) too -- a bare "2" reads as ambiguous
        # (rank? gap? hole?) without the column name a desktop <th> gives it.
        value = " · ".join(escape(f"{c}: {row[c]}") for c in headline_cols)
        primary = f'<span class="bl-player">{player_html}</span><span class="bl-value">{value}</span>'
        # Context values are bare numbers/labels with no self-evident unit
        # (Rank After R3, Hole of Max Lead, ...); prefix each with its column
        # name so the sub-line reads as facts, not an unlabeled number dump.
        # 'TEG' already reads as "TEG 7" in the data, so it's left bare.
        sub = " · ".join(
            str(row[c]) if c == "TEG" else f"{c} {row[c]}" for c in context_cols
        )
        rows_html.append(_byline_row_html(primary, sub, "cb-row"))
    return _byline_list_html(rows_html, "cb-list")


def _comebacks_context(competition: str = "gross", n: int = 5) -> dict:
    """Build sections for the comebacks page."""
    try:
        all_data = cached_load_all_data()
        round_info = read_file(ROUND_INFO_CSV)
        measure = "GrossVP" if competition == "gross" else "Stableford"

        def fmt(df):
            return _fmt_comebacks(df, measure)

        sections = []

        # 1. Best & Worst Final Rounds
        # Columns: TEG, Player, Final Round, Final Round Score, Rank After R3,
        # Total Score, Final Rank. Headline = Final Round Score (that's the
        # table's whole point); context = everything else.
        differentials = calculate_final_round_differentials(all_data, round_info, measure)
        if differentials is not None and not differentials.empty:
            best_fmt = fmt(differentials.head(n))
            sections.append({
                "title": "Best Final Round Performances",
                "table_html": _df_to_html(best_fmt) + _build_comebacks_byline_html(
                    best_fmt, "Player", ["Final Round Score"],
                    ["TEG", "Final Round", "Rank After R3", "Total Score", "Final Rank"]),
            })
            worst_fmt = fmt(differentials.tail(n).iloc[::-1])
            sections.append({
                "title": "Worst Final Round Performances",
                "table_html": _df_to_html(worst_fmt) + _build_comebacks_byline_html(
                    worst_fmt, "Player", ["Final Round Score"],
                    ["TEG", "Final Round", "Rank After R3", "Total Score", "Final Rank"]),
            })

            # Worst performances by leaders going into the final round (Rank After R3 == 1)
            leaders = differentials[differentials["Rank After R3"] == 1.0].copy()
            if not leaders.empty:
                leaders = leaders.sort_values("Final Round Score", ascending=(measure != "GrossVP"))
                leaders_fmt = fmt(leaders.head(n))
                sections.append({
                    "title": "Worst Final Round Performances by Leaders",
                    "caption": "Leaders going into the final round (Rank After R3 = 1)",
                    "table_html": _df_to_html(leaders_fmt) + _build_comebacks_byline_html(
                        leaders_fmt, "Player", ["Final Round Score"],
                        ["TEG", "Final Round", "Rank After R3", "Total Score", "Final Rank"]),
                })
        else:
            sections.append({"title": "Best & Worst Final Rounds", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 2. Biggest Leads Lost After R3
        # Columns: TEG, Leader After R3, Gap to 2nd, Winner, Leader Final
        # Position. Identity column is 'Leader After R3', not 'Player' --
        # headline = Gap to 2nd (the size of the lost lead).
        leads_r3 = calculate_biggest_leads_lost_after_r3(all_data, round_info, measure)
        if leads_r3 is not None and not leads_r3.empty:
            leads_r3_fmt = fmt(leads_r3.head(n))
            sections.append({
                "title": "Biggest Leads Lost Going Into Final Round",
                "table_html": _df_to_html(leads_r3_fmt) + _build_comebacks_byline_html(
                    leads_r3_fmt, "Leader After R3", ["Gap to 2nd"],
                    ["TEG", "Winner", "Leader Final Position"]),
            })
        else:
            sections.append({"title": "Biggest Leads Lost Going Into Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 3. Biggest Leads Lost During R4
        # Columns: TEG, Player, Max Lead in R4, Hole of Max Lead, Winner,
        # Final Gap. Headline = Max Lead in R4.
        leads_r4 = calculate_biggest_leads_lost_in_r4(all_data, round_info, measure)
        if leads_r4 is not None and not leads_r4.empty:
            leads_r4_fmt = fmt(leads_r4.head(n))
            sections.append({
                "title": "Biggest Leads Lost During Final Round",
                "table_html": _df_to_html(leads_r4_fmt) + _build_comebacks_byline_html(
                    leads_r4_fmt, "Player", ["Max Lead in R4"],
                    ["TEG", "Hole of Max Lead", "Winner", "Final Gap"]),
            })
        else:
            sections.append({"title": "Biggest Leads Lost During Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 4. Biggest Comebacks
        # Columns: TEG, Player, Gap After R3, Player R4 Score, Leader R4
        # Score, Gap Closed, Final Position, Winner. Headline = Gap Closed
        # (the table's title is literally about that figure).
        comebacks = calculate_biggest_comebacks(all_data, round_info, measure)
        if comebacks is not None and not comebacks.empty:
            comebacks_fmt = fmt(comebacks.head(n))
            sections.append({
                "title": "Biggest Comebacks in Final Round",
                "table_html": _df_to_html(comebacks_fmt) + _build_comebacks_byline_html(
                    comebacks_fmt, "Player", ["Gap Closed"],
                    ["TEG", "Gap After R3", "Player R4 Score", "Leader R4 Score", "Final Position", "Winner"]),
            })
        else:
            sections.append({"title": "Biggest Comebacks in Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        caption = ("Analysis covers completed TEGs from TEG 2 onwards. "
                   "'Gap Closed' measures ground made up on the leader during the final round.")
        return {"sections": sections, "caption": caption}
    except Exception as e:
        logger.exception("_comebacks_context failed")
        return {"error": str(e)}


@router.get("/scoring/comebacks")
def scoring_comebacks_page(
    request: Request,
    competition: str = Query("gross"),
    n: int = Query(5),
):
    ctx = _comebacks_context(competition, n)
    return templates.TemplateResponse("scoring_comebacks.html", {
        "request": request,
        "active_page": "scoring",
        "competition": competition,
        "n_records": n,
        **ctx,
    })


@router.get("/scoring/comebacks/content")
def scoring_comebacks_content(
    request: Request,
    competition: str = Query("gross"),
    n: int = Query(5),
):
    ctx = _comebacks_context(competition, n)
    return templates.TemplateResponse("partials/scoring_comebacks_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/heatmap ---------------------------------------------------------

HEATMAP_ROWS = [("Player", "Player"), ("Course", "Course"), ("TEGNum", "TEG")]

# Dimensions the columns can be grouped by. Value = data column, label = display.
HEATMAP_COLS = [
    ("Hole", "Hole"),
    ("SI", "Stroke Index"),
    ("PAR", "Par"),
    ("TEGNum", "TEG"),
    ("Course", "Course"),
    ("Area", "Region"),
]

# Column dimensions whose values are numeric (sorted/labelled as numbers).
_HM_NUMERIC_COLS = {"Hole", "SI", "PAR", "TEGNum"}

# Diverging palettes: 7 steps, index 0 = best/low, 6 = worst/high.
# Each entry is (background_hex, text_hex).
_HM_PALETTE_OPTIONS = [
    ("redyellowblue",    "Red-Yellow-Blue"),
    ("redblue",          "Red-Blue"),
    ("spectral",         "Spectral"),
    ("pinkyellowgreen",  "Pink-Yellow-Green"),
    ("purpleorange",     "Purple-Orange"),
    ("redgrey",          "Red-Grey"),
    ("blueorange",       "Blue-Orange"),
]
_HM_PALETTES: dict[str, list[tuple[str, str]]] = {
    "redyellowblue": [
        ("#4575b4", "#fff"),   ("#74add1", "#1a1a1a"), ("#abd9e9", "#1a1a1a"),
        ("#ffffbf", "#555"),
        ("#fdae61", "#1a1a1a"), ("#f46d43", "#fff"),   ("#d73027", "#fff"),
    ],
    "redblue": [
        ("#2166ac", "#fff"),   ("#4393c3", "#fff"),    ("#92c5de", "#1a1a1a"),
        ("#f7f7f7", "#888"),
        ("#f4a582", "#1a1a1a"), ("#d6604d", "#fff"),   ("#b2182b", "#fff"),
    ],
    "spectral": [
        ("#2b83ba", "#fff"),   ("#76b9d0", "#1a1a1a"), ("#b7dbe7", "#1a1a1a"),
        ("#ffffbf", "#555"),
        ("#fdcc8a", "#1a1a1a"), ("#f4883f", "#fff"),   ("#d7191c", "#fff"),
    ],
    "pinkyellowgreen": [
        ("#1a7837", "#fff"),   ("#4dac26", "#fff"),    ("#b8e186", "#1a1a1a"),
        ("#f7f7f7", "#888"),
        ("#e9a3c9", "#1a1a1a"), ("#c51b7d", "#fff"),   ("#8e0152", "#fff"),
    ],
    "purpleorange": [
        ("#542788", "#fff"),   ("#8073ac", "#fff"),    ("#b2abd2", "#1a1a1a"),
        ("#f7f7f7", "#888"),
        ("#fee0b6", "#1a1a1a"), ("#e08214", "#fff"),   ("#b35806", "#fff"),
    ],
    "redgrey": [
        ("#4d4d4d", "#fff"),   ("#878787", "#fff"),    ("#bababa", "#1a1a1a"),
        ("#f7f7f7", "#888"),
        ("#fddbc7", "#1a1a1a"), ("#ef8a62", "#1a1a1a"), ("#b2182b", "#fff"),
    ],
    "blueorange": [
        ("#2166ac", "#fff"),   ("#4393c3", "#fff"),    ("#92c5de", "#1a1a1a"),
        ("#f7f7f7", "#888"),
        ("#fdb863", "#1a1a1a"), ("#e08214", "#fff"),   ("#b35806", "#fff"),
    ],
}


def _hm_col_label(col_by: str, val) -> str:
    """Header label for a heatmap column value."""
    if col_by in _HM_NUMERIC_COLS:
        return str(int(val))
    return str(val)


def _hm_bucket(val: float, domain_min: float, domain_mid: float, domain_max: float) -> int:
    """Map val to a palette index 0 (best/low) .. 6 (worst/high) using a
    piecewise-linear diverging scale anchored at min, mid, and max."""
    if val <= domain_min:
        return 0
    if val >= domain_max:
        return 6
    if val <= domain_mid:
        t = (val - domain_min) / (domain_mid - domain_min)
        return max(0, min(3, round(t * 3)))
    t = (val - domain_mid) / (domain_max - domain_mid)
    return max(3, min(6, 3 + round(t * 3)))


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hm_cell_style(val: float, colors: list, domain_min: float, domain_mid: float,
                   domain_max: float) -> str:
    """Return an inline style string using continuous colour interpolation.

    The 7-stop palette is treated as a smooth gradient; the value's position
    in the [min→mid→max] domain maps to a continuous [0..1] and the colour
    is interpolated between adjacent stops rather than bucketed.
    """
    if pd.isna(val):
        return "background:#e8e8e5;color:#aaa"

    # Continuous position in [0..1] across the piecewise-linear domain
    if val <= domain_min:
        t = 0.0
    elif val >= domain_max:
        t = 1.0
    elif val <= domain_mid:
        t = 0.5 * (val - domain_min) / (domain_mid - domain_min)
    else:
        t = 0.5 + 0.5 * (val - domain_mid) / (domain_max - domain_mid)

    # Interpolate between adjacent palette stops
    n = len(colors) - 1  # 6 segments for 7 stops
    pos = t * n
    lo = min(int(pos), n - 1)
    hi = lo + 1
    frac = pos - lo

    bg_lo, _ = colors[lo]
    bg_hi, _ = colors[hi]
    r1, g1, b1 = _hex_to_rgb(bg_lo)
    r2, g2, b2 = _hex_to_rgb(bg_hi)
    r = round(r1 + (r2 - r1) * frac)
    g = round(g1 + (g2 - g1) * frac)
    b = round(b1 + (b2 - b1) * frac)

    # Text colour: nearest stop (avoids interpolating two text colours)
    _, fg = colors[round(t * n)]
    return f"background:rgb({r},{g},{b});color:{fg}"


def _hm_legend_html(colors: list, domain_min: float, domain_mid: float,
                    domain_max: float) -> str:
    """Build a 7-swatch colour-bar legend with min/mid/max labels."""
    swatches = "".join(
        f"<span class='hm-swatch' style='background:{bg}'></span>"
        for bg, _ in colors
    )
    return (
        f"<div class='hm-legend'>"
        f"<span class='hm-legend-end'>Better</span>"
        f"<div class='hm-legend-bar'>{swatches}</div>"
        f"<span class='hm-legend-end'>Worse</span>"
        f"<span class='hm-legend-range'>"
        f"min&nbsp;{domain_min:.1f} &middot; mid&nbsp;{domain_mid:.1f} &middot; max&nbsp;{domain_max:.1f}"
        f"</span>"
        f"</div>"
    )


def _heatmap_context(
    row_by: str = "Player",
    col_by: str = "Hole",
    sort_by_score: bool = True,
    show_col_totals: bool = False,
    show_row_avg: bool = False,
    palette: str = "redyellowblue",
    reverse: bool = False,
    domain_min: float | None = None,
    domain_mid: float | None = None,
    domain_max: float | None = None,
) -> dict:
    """Build heatmap table HTML + legend for mean GrossVP per (row_by, col_by)."""
    try:
        if row_by == col_by:
            return {"error": "Rows and columns can't use the same dimension — pick a different columns option."}

        all_data = cached_load_all_data()

        # Cell values: mean GrossVP per (row, col)
        agg = all_data.groupby([row_by, col_by], as_index=False)['GrossVP'].mean()
        cell = {(r[row_by], r[col_by]): r['GrossVP'] for _, r in agg.iterrows()}

        # Column order
        col_vals = all_data[col_by].dropna().unique().tolist()
        if col_by in _HM_NUMERIC_COLS:
            col_vals = sorted(col_vals, key=lambda x: int(x))
        else:
            col_vals = sorted(col_vals, key=lambda x: str(x))

        # Overall row averages (true mean) — sorting + optional Avg column
        row_avgs = all_data.groupby(row_by)['GrossVP'].mean()
        if sort_by_score:
            row_labels = row_avgs.sort_values(ascending=False).index.tolist()
        else:
            row_labels = sorted(row_avgs.index.tolist(),
                                key=lambda x: (int(x) if str(x).isdigit() else 0, str(x)))

        # Auto-compute sensible domain defaults from cell-value distribution
        all_cell_vals = [v for v in cell.values() if not pd.isna(v)]
        s = pd.Series(all_cell_vals) if all_cell_vals else pd.Series([0.0])
        auto_mid = round(float(s.mean()), 2)
        auto_std = max(float(s.std()) if len(s) > 1 else 0.3, 0.05)
        auto_min = round(auto_mid - 1.5 * auto_std, 2)
        auto_max = round(auto_mid + 1.5 * auto_std, 2)

        dm_min = domain_min if domain_min is not None else auto_min
        dm_mid = domain_mid if domain_mid is not None else auto_mid
        dm_max = domain_max if domain_max is not None else auto_max
        # Guard: ensure min < mid < max
        if not (dm_min < dm_mid < dm_max):
            dm_min, dm_mid, dm_max = auto_min, auto_mid, auto_max

        colors = list(_HM_PALETTES.get(palette, _HM_PALETTES["redyellowblue"]))
        if reverse:
            colors = list(reversed(colors))

        # Rotate string-type column headers for compact equal-width columns
        rotate_headers = col_by not in _HM_NUMERIC_COLS
        th_cls = " class='rotated-header'" if rotate_headers else ""

        # teg-table gives Roboto Mono + base styling; heatmap-table overrides
        # spacing/padding via higher-specificity double-class selectors in heatmap.css
        html = ["<table class='teg-table heatmap-table'>"]
        html.append("<thead><tr><th class='hm-row-label-header'></th>")
        for c in col_vals:
            html.append(f"<th{th_cls}><span>{_hm_col_label(col_by, c)}</span></th>")
        if show_row_avg:
            html.append("<th class='hm-avg-header'><span>Avg</span></th>")
        html.append("</tr></thead><tbody>")

        for label in row_labels:
            row_avg = row_avgs.get(label, float('nan'))
            display_label = f"TEG {label}" if row_by == "TEGNum" else str(label)
            html.append(f"<tr><td class='row-label'>{display_label}</td>")
            for c in col_vals:
                v = cell.get((label, c), float('nan'))
                sty = _hm_cell_style(v, colors, dm_min, dm_mid, dm_max)
                txt = f"{v:+.1f}" if not pd.isna(v) else ""
                html.append(f"<td style='{sty}'>{txt}</td>")
            if show_row_avg:
                sty = _hm_cell_style(row_avg, colors, dm_min, dm_mid, dm_max)
                ra = f"{row_avg:+.1f}" if not pd.isna(row_avg) else ""
                html.append(f"<td style='{sty}' class='hm-avg-cell'>{ra}</td>")
            html.append("</tr>")

        if show_col_totals:
            col_tot = all_data.groupby(col_by)['GrossVP'].mean()
            total_avg = all_data['GrossVP'].mean()
            html.append("<tr class='hm-total-row'><td class='row-label hm-total-label'>TOTAL</td>")
            for c in col_vals:
                v = col_tot.get(c, float('nan'))
                sty = _hm_cell_style(v, colors, dm_min, dm_mid, dm_max)
                txt = f"{v:+.1f}" if not pd.isna(v) else ""
                html.append(f"<td style='{sty}' class='hm-total-cell'>{txt}</td>")
            if show_row_avg:
                sty = _hm_cell_style(total_avg, colors, dm_min, dm_mid, dm_max)
                html.append(f"<td style='{sty}' class='hm-avg-cell hm-total-cell'>{total_avg:+.1f}</td>")
            html.append("</tr>")

        html.append("</tbody></table>")

        result = {
            "table_html": "".join(html),
            "legend_html": _hm_legend_html(colors, dm_min, dm_mid, dm_max),
            "domain_min": dm_min,
            "domain_mid": dm_mid,
            "domain_max": dm_max,
        }

        # Mobile transpose: only for the default Player x Hole view (19 columns
        # including the row-label column, too dense to fit phone width without
        # scroll). Hole-rows/initials-columns is what "transposing" that grid
        # means and fits in ~8 columns. Any other row/col pick the user chose
        # via the dropdowns is left as-is on mobile (existing scrollable
        # table, no transposed view) -- out of scope per design review.
        # Reuse the resolved domain (dm_min/dm_mid/dm_max) rather than the
        # raw params so the transposed table's heat colours match the
        # primary table exactly, including any user-set range override.
        if row_by == "Player" and col_by == "Hole":
            mobile = _heatmap_context(
                row_by="Hole", col_by="Pl",
                sort_by_score=sort_by_score,
                show_col_totals=show_col_totals,
                show_row_avg=show_row_avg,
                palette=palette,
                reverse=reverse,
                domain_min=dm_min, domain_mid=dm_mid, domain_max=dm_max,
            )
            if "table_html" in mobile:
                result["table_html_mobile"] = mobile["table_html"]

        return result
    except Exception as e:
        logger.exception("_heatmap_context failed")
        return {"error": str(e)}


def _parse_checkbox(val: str | None) -> bool:
    """Parse HTMX checkbox value: present='true' means checked, absent=None means unchecked."""
    return val is not None and val.lower() == "true"


@router.get("/scoring/heatmap")
def scoring_heatmap_page(
    request: Request,
    row_by: str = Query("Player"),
    col_by: str = Query("Hole"),
    sort_by_score: str = Query("true"),
    show_col_totals: str | None = Query(None),
    show_row_avg: str | None = Query(None),
    palette: str = Query("redyellowblue"),
    reverse: str | None = Query(None),
    domain_min: float | None = Query(None),
    domain_mid: float | None = Query(None),
    domain_max: float | None = Query(None),
):
    sbs = _parse_checkbox(sort_by_score)
    sct = _parse_checkbox(show_col_totals)
    sra = _parse_checkbox(show_row_avg)
    rev = _parse_checkbox(reverse)
    ctx = _heatmap_context(row_by, col_by, sbs, sct, sra, palette, rev, domain_min, domain_mid, domain_max)
    return templates.TemplateResponse("scoring_heatmap.html", {
        "request": request,
        "active_page": "scoring",
        "wide": True,
        "row_options": HEATMAP_ROWS,
        "col_options": HEATMAP_COLS,
        "palette_options": _HM_PALETTE_OPTIONS,
        "row_by": row_by,
        "col_by": col_by,
        "sort_by_score": sbs,
        "show_col_totals": sct,
        "show_row_avg": sra,
        "palette": palette,
        "reverse": rev,
        **ctx,
    })


@router.get("/scoring/heatmap/content")
def scoring_heatmap_content(
    request: Request,
    row_by: str = Query("Player"),
    col_by: str = Query("Hole"),
    sort_by_score: str | None = Query(None),
    show_col_totals: str | None = Query(None),
    show_row_avg: str | None = Query(None),
    palette: str = Query("redyellowblue"),
    reverse: str | None = Query(None),
    domain_min: float | None = Query(None),
    domain_mid: float | None = Query(None),
    domain_max: float | None = Query(None),
):
    sbs = _parse_checkbox(sort_by_score)
    sct = _parse_checkbox(show_col_totals)
    sra = _parse_checkbox(show_row_avg)
    rev = _parse_checkbox(reverse)
    ctx = _heatmap_context(row_by, col_by, sbs, sct, sra, palette, rev, domain_min, domain_mid, domain_max)
    return templates.TemplateResponse("partials/scoring_heatmap_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/round-distribution ----------------------------------------------

ROUND_DIST_BIN_WIDTH = 5
ROUND_DIST_RANGES = [("all", "All TEGs"), ("last5", "Last 5 TEGs"), ("last10", "Last 10 TEGs")]


def _round_distribution_chart(edges: list[int], counts: list[int], mean: float | None) -> str:
    """Single-player round-score histogram: one consistent colour across every
    panel (player identity already comes from the card heading, so a legend
    or per-player hue would be redundant), fixed numeric x-axis so bars line
    up across panels, and a dashed mean marker."""
    import plotly.graph_objects as go
    import plotly.express as px

    width = edges[1] - edges[0]
    x_mid = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    customdata = [[edges[i], edges[i + 1]] for i in range(len(edges) - 1)]

    fig = go.Figure(go.Bar(
        x=x_mid,
        y=counts,
        width=width * 0.88,
        marker=dict(color=px.colors.qualitative.Plotly[0]),
        customdata=customdata,
        hovertemplate='%{customdata[0]}–%{customdata[1]}: %{y} round(s)<extra></extra>',
    ))
    if mean is not None:
        fig.add_vline(x=mean, line=dict(color="rgba(0,0,0,0.35)", width=1.5, dash="dash"))

    fig.update_layout(
        bargap=0.06,
        showlegend=False,
        margin=dict(r=8, t=6, b=22, l=26),
        font=dict(family="monospace", size=10),
    )
    fig.update_xaxes(tickvals=edges, range=[edges[0], edges[-1]], fixedrange=True)
    fig.update_yaxes(fixedrange=True, rangemode="tozero")
    fig.update_layout(**get_chart_style('streamlit'))
    return fig.to_json()


def _round_distribution_context(range_key: str = "all") -> dict:
    try:
        rd = cached_round_data()
        if range_key not in dict(ROUND_DIST_RANGES):
            range_key = "all"

        teg_nums = sorted(rd['TEGNum'].unique().tolist())
        if range_key == "last5":
            keep = set(teg_nums[-5:])
        elif range_key == "last10":
            keep = set(teg_nums[-10:])
        else:
            keep = set(teg_nums)
        filtered = rd[rd['TEGNum'].isin(keep)]

        # Bin edges are computed from the FULL history, not the filtered
        # subset, so the x-axis never shifts when the TEG-range filter
        # changes -- shapes stay comparable across players and across filters.
        all_scores = rd['Sc'].dropna()
        w = ROUND_DIST_BIN_WIDTH
        lo = int(all_scores.min() // w * w)
        hi = int((all_scores.max() // w + 1) * w)
        edges = list(range(lo, hi + w, w))

        # Most rounds played (all-time) first.
        player_order = rd.groupby('Player')['Sc'].count().sort_values(ascending=False).index.tolist()

        panels = []
        for player in player_order:
            p_scores = filtered.loc[filtered['Player'] == player, 'Sc'].dropna()
            n = len(p_scores)
            mean = round(float(p_scores.mean()), 1) if n else None
            counts = pd.cut(p_scores, bins=edges, right=False).value_counts(sort=False).tolist()
            panels.append({
                "player": player,
                "n": n,
                "min": int(p_scores.min()) if n else None,
                "max": int(p_scores.max()) if n else None,
                "mean": mean,
                "chart_json": _round_distribution_chart(edges, counts, mean) if n else None,
            })

        return {
            "panels": panels,
            "ranges": ROUND_DIST_RANGES,
            "selected_range": range_key,
        }
    except Exception as e:
        logger.exception("_round_distribution_context failed")
        return {"error": str(e)}


@router.get("/scoring/round-distribution")
def scoring_round_distribution_page(request: Request, range: str = Query("all")):
    ctx = _round_distribution_context(range)
    return templates.TemplateResponse("scoring_round_distribution.html", {
        "request": request,
        "active_page": "scoring",
        **ctx,
    })


@router.get("/scoring/round-distribution/content")
def scoring_round_distribution_content(request: Request, range: str = Query("all")):
    ctx = _round_distribution_context(range)
    return templates.TemplateResponse("partials/scoring_round_distribution_content.html", {
        "request": request,
        **ctx,
    })
