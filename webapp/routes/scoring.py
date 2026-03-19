"""Scoring section routes: /scoring/*."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.scoring import (
    calculate_par_performance_matrix,
    format_par_performance_table,
    count_scores_by_player,
    prepare_score_count_display,
    prepare_achievement_table_data,
    get_scoring_achievement_fields,
)
from teg_analysis.analysis.streaks import (
    prepare_good_streaks_data, prepare_bad_streaks_data,
    prepare_current_good_streaks_data, prepare_current_bad_streaks_data,
    prepare_record_best_streaks_data, prepare_record_worst_streaks_data,
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
from teg_analysis.display.tables import score_type_stats, max_scoretype_per_round
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    get_available_teg_numbers,
    get_default_teg_num,
    get_rounds_for_teg,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


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
            stats = score_type_stats(all_data)
            sections.append({"title": f"{score_type} Stats by Player", "table_html": _df_to_html(stats)})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/birdies")
async def scoring_birdies_page(request: Request):
    ctx = _birdies_tab_context("career", "Birdies")
    return templates.TemplateResponse("scoring_birdies.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": BIRDIES_TABS,
        "active_tab": "career",
        "score_type": "Birdies",
        "score_types": [label for label, _ in BIRDIES_SCORE_TYPES],
        **ctx,
    })


@router.get("/scoring/birdies/tab")
async def scoring_birdies_tab(request: Request, tab: str = Query("career"), score_type: str = Query("Birdies")):
    ctx = _birdies_tab_context(tab, score_type)
    return templates.TemplateResponse("partials/scoring_birdies_tab.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/streaks ---------------------------------------------------------

STREAK_TABS = [
    ("player", "Streaks by Player"),
    ("records", "Record Streaks"),
]


def _streak_tab_context(tab: str, direction: str = "good", mode: str = "max") -> dict:
    """Build sections list for a given streaks tab."""
    try:
        all_data = cached_load_all_data()
        sections = []

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

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/streaks")
async def scoring_streaks_page(request: Request):
    active_tab = "player"
    direction = "good"
    mode = "max"
    ctx = _streak_tab_context(active_tab, direction, mode)
    return templates.TemplateResponse("scoring_streaks.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": STREAK_TABS,
        "active_tab": active_tab,
        "direction": direction,
        "mode": mode,
        **ctx,
    })


@router.get("/scoring/streaks/tab")
async def scoring_streaks_tab(
    request: Request,
    tab: str = Query("player"),
    direction: str = Query("good"),
    mode: str = Query("max"),
):
    ctx = _streak_tab_context(tab, direction, mode)
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
        return {"table_html": _df_to_html(formatted)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/by-par")
async def scoring_by_par_page(request: Request, teg: int = Query(0)):
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
async def scoring_by_par_content(request: Request, teg: int = Query(0)):
    ctx = _by_par_context(teg)
    return templates.TemplateResponse("partials/scoring_matrix_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/by-teg ----------------------------------------------------------

def _by_teg_chart(agg: pd.DataFrame) -> str:
    """Build a Plotly line chart of GrossVP by TEG per player, return JSON."""
    import plotly.graph_objects as go
    import json

    fig = go.Figure()
    for player in sorted(agg['Player'].unique()):
        pdata = agg[agg['Player'] == player].sort_values('TEGNum')
        fig.add_trace(go.Scatter(
            x=pdata['TEGNum'], y=pdata['GrossVP'],
            mode='lines+markers', name=player,
            line=dict(width=2), marker=dict(size=4),
        ))

    fig.update_layout(
        xaxis_title='TEG', yaxis_title='Avg Gross vs Par',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(r=20, t=10, b=40, l=50),
        font=dict(family="monospace"),
    )
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    return json.dumps(fig, cls=go.utils.PlotlyJSONEncoder)


@router.get("/scoring/by-teg")
async def scoring_by_teg_page(request: Request):
    chart_json = None
    try:
        all_data = cached_load_all_data()
        agg = aggregate_data(all_data, 'TEG', measures=['GrossVP'])
        pivot = agg.pivot_table(index='TEGNum', columns='Player', values='GrossVP', aggfunc='first')
        pivot = pivot.round(1).reset_index().rename(columns={'TEGNum': 'TEG'})
        table_html = _df_to_html(pivot)
        chart_json = _by_teg_chart(agg)
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("scoring_by_teg.html", {
        "request": request,
        "active_page": "scoring",
        "table_html": table_html,
        "chart_json": chart_json,
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
                sections.append({"title": "Course Records (Gross)", "table_html": _df_to_html(df)})

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
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Player', aggfunc='mean')
            # Add Total column
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].mean()
            pivot = pivot.round(1).reset_index()
            pivot.columns.name = None
            # Format numeric cells
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 1))
            sections.append({"title": "Average Gross vs Par by Course", "table_html": _df_to_html(pivot)})

        elif tab == "bests":
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Player', aggfunc='min')
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].min()
            pivot = pivot.reset_index()
            pivot.columns.name = None
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 0))
            sections.append({"title": "Best Gross vs Par by Course", "table_html": _df_to_html(pivot)})

        elif tab == "worsts":
            pivot = rd_data.pivot_table(values='GrossVP', index='Course', columns='Player', aggfunc='max')
            pivot['Total'] = rd_data.groupby('Course')['GrossVP'].max()
            pivot = pivot.reset_index()
            pivot.columns.name = None
            for col in pivot.columns:
                if col != 'Course':
                    pivot[col] = pivot[col].apply(lambda v: _format_vp(v, 0))
            sections.append({"title": "Worst Gross vs Par by Course", "table_html": _df_to_html(pivot)})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/by-course")
async def scoring_by_course_page(request: Request, area: str = Query("All Areas")):
    areas = _get_course_areas()
    active_tab = "gross_records"
    ctx = _course_tab_context(active_tab, area)
    return templates.TemplateResponse("scoring_by_course.html", {
        "request": request,
        "active_page": "scoring",
        "tabs": COURSE_TABS,
        "active_tab": active_tab,
        "areas": areas,
        "selected_area": area,
        **ctx,
    })


@router.get("/scoring/by-course/tab")
async def scoring_by_course_tab(request: Request, tab: str = Query("gross_records"), area: str = Query("All Areas")):
    ctx = _course_tab_context(tab, area)
    return templates.TemplateResponse("partials/scoring_by_course_tab.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/all-rounds ------------------------------------------------------

@router.get("/scoring/all-rounds")
async def scoring_all_rounds_page(request: Request):
    try:
        rd_data = cached_round_data()
        display_cols = [c for c in ['TEGNum', 'Round', 'Player', 'Course', 'GrossVP', 'Stableford'] if c in rd_data.columns]
        display = rd_data[display_cols].sort_values(['TEGNum', 'Round', 'GrossVP'], ascending=[False, True, True])
        display = display.rename(columns={'TEGNum': 'TEG', 'GrossVP': 'Gross vs Par'})
        table_html = _df_to_html(display)
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "scoring",
        "title": "All Rounds",
        "subtitle": "Complete round-level scoring data",
        "table_html": table_html,
        "sections": None,
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

        # Add Average column
        pivot['Average'] = pivot.mean(axis=1).round(1)

        pivot = pivot.round(1).reset_index()
        if 'TEGNum' in pivot.columns:
            pivot = pivot.rename(columns={'TEGNum': 'TEG'})
        table_html = _df_to_html(pivot)
        return {"table_html": table_html}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/matrix")
async def scoring_matrix_page(request: Request):
    ctx = _matrix_context("teg", "GrossVP")
    return templates.TemplateResponse("scoring_matrix.html", {
        "request": request,
        "active_page": "scoring",
        "levels": MATRIX_LEVELS,
        "score_types": MATRIX_TYPES,
        "selected_level": "teg",
        "selected_type": "GrossVP",
        **ctx,
    })


@router.get("/scoring/matrix/content")
async def scoring_matrix_content(request: Request, level: str = Query("teg"), score_type: str = Query("GrossVP")):
    ctx = _matrix_context(level, score_type)
    return templates.TemplateResponse("partials/scoring_matrix_content.html", {
        "request": request,
        **ctx,
    })


# --- /scoring/distributions ---------------------------------------------------

def _distributions_chart(display: pd.DataFrame) -> str | None:
    """Build a grouped bar chart of score distributions by player, return JSON."""
    try:
        import plotly.graph_objects as go
        import plotly.utils
        import json

        if display is None or display.empty:
            return None

        # First column is the score label, rest are players
        score_col = display.columns[0]
        player_cols = [c for c in display.columns[1:] if c not in ('Total',)]

        fig = go.Figure()
        for player in player_cols:
            fig.add_trace(go.Bar(
                x=display[score_col],
                y=pd.to_numeric(display[player], errors='coerce'),
                name=player,
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Score vs Par',
            yaxis_title='Count',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(r=20, t=10, b=40, l=50),
            font=dict(family="monospace"),
        )
        fig.layout.xaxis.fixedrange = True
        fig.layout.yaxis.fixedrange = True

        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    except Exception:
        return None


@router.get("/scoring/distributions")
async def scoring_distributions_page(request: Request):
    chart_json = None
    try:
        all_data = cached_load_all_data()
        counts = count_scores_by_player(all_data)
        display = prepare_score_count_display(counts, 'GrossVP', 'Gross vs Par')
        table_html = _df_to_html(display)
        chart_json = _distributions_chart(display)
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("scoring_distributions.html", {
        "request": request,
        "active_page": "scoring",
        "table_html": table_html,
        "chart_json": chart_json,
    })


# --- /scoring/changes ---------------------------------------------------------

@router.get("/scoring/changes")
async def scoring_changes_page(request: Request):
    try:
        rd_data = cached_round_data()
        # Calculate round-over-round changes per player per TEG
        changes_list = []
        for teg_num in sorted(rd_data['TEGNum'].unique()):
            teg_rd = rd_data[rd_data['TEGNum'] == teg_num].sort_values(['Player', 'Round'])
            for player in teg_rd['Player'].unique():
                player_rounds = teg_rd[teg_rd['Player'] == player].sort_values('Round')
                prev = None
                for _, row in player_rounds.iterrows():
                    if prev is not None:
                        diff = row['GrossVP'] - prev
                        changes_list.append({
                            'TEG': teg_num,
                            'Round': row['Round'],
                            'Player': player,
                            'Gross vs Par': row['GrossVP'],
                            'Change': f"{diff:+.0f}" if diff != 0 else "=",
                        })
                    prev = row['GrossVP']

        if changes_list:
            df = pd.DataFrame(changes_list)
            df = df.sort_values(['TEG', 'Round', 'Player'], ascending=[False, True, True])
            table_html = _df_to_html(df)
        else:
            table_html = "<p class='text-muted'>No round data available.</p>"
    except Exception as e:
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "scoring",
        "title": "Changes vs Previous Round",
        "subtitle": "How each player's score changed from the previous round",
        "table_html": table_html,
        "sections": None,
    })


# --- /scoring/comebacks -------------------------------------------------------

def _comebacks_context(competition: str = "gross", n: int = 5) -> dict:
    """Build sections for the comebacks page."""
    try:
        all_data = cached_load_all_data()
        round_info = read_file(ROUND_INFO_CSV)
        measure = "GrossVP" if competition == "gross" else "Stableford"

        sections = []

        # 1. Best & Worst Final Rounds
        differentials = calculate_final_round_differentials(all_data, round_info, measure)
        if differentials is not None and not differentials.empty:
            sections.append({"title": "Best Final Round Performances", "table_html": _df_to_html(differentials.head(n))})
            worst = differentials.tail(n).iloc[::-1]
            sections.append({"title": "Worst Final Round Performances", "table_html": _df_to_html(worst)})
        else:
            sections.append({"title": "Best & Worst Final Rounds", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 2. Biggest Leads Lost After R3
        leads_r3 = calculate_biggest_leads_lost_after_r3(all_data, round_info, measure)
        if leads_r3 is not None and not leads_r3.empty:
            sections.append({"title": "Biggest Leads Lost Going Into Final Round", "table_html": _df_to_html(leads_r3.head(n))})
        else:
            sections.append({"title": "Biggest Leads Lost Going Into Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 3. Biggest Leads Lost During R4
        leads_r4 = calculate_biggest_leads_lost_in_r4(all_data, round_info, measure)
        if leads_r4 is not None and not leads_r4.empty:
            sections.append({"title": "Biggest Leads Lost During Final Round", "table_html": _df_to_html(leads_r4.head(n))})
        else:
            sections.append({"title": "Biggest Leads Lost During Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        # 4. Biggest Comebacks
        comebacks = calculate_biggest_comebacks(all_data, round_info, measure)
        if comebacks is not None and not comebacks.empty:
            sections.append({"title": "Biggest Comebacks in Final Round", "table_html": _df_to_html(comebacks.head(n))})
        else:
            sections.append({"title": "Biggest Comebacks in Final Round", "table_html": "<p class='text-muted text-sm'>No data available.</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scoring/comebacks")
async def scoring_comebacks_page(
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
async def scoring_comebacks_content(
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


def _heatmap_color(val: float) -> str:
    """Map avg GrossVP to a CSS background colour. Green=under par, red=over par."""
    if pd.isna(val):
        return "background-color: #f5f5f5"
    # Clamp magnitude at 3 for full saturation
    clamped = max(-3.0, min(3.0, val))
    t = abs(clamped) / 3.0  # 0..1
    # Lightness: 97% at par (white-ish), 40% at full saturation
    lightness = 97 - (57 * t)
    if val < 0:
        hue = 120  # green
    elif val > 0:
        hue = 0    # red
    else:
        return "background-color: hsl(0, 0%, 97%)"
    return f"background-color: hsl({hue}, 50%, {lightness:.0f}%)"


def _heatmap_context(row_by: str = "Player", sort_by_score: bool = True, show_totals: bool = True) -> dict:
    """Build heatmap table HTML."""
    try:
        all_data = cached_load_all_data()
        holes = list(range(1, 19))

        # Group by (row_by, Hole), calc mean GrossVP
        agg = all_data.groupby([row_by, 'Hole'], as_index=False)['GrossVP'].mean()
        agg.rename(columns={'GrossVP': 'AvgGrossVP'}, inplace=True)

        # Get unique row labels
        row_labels = agg[row_by].unique().tolist()

        # Sort rows
        if sort_by_score:
            row_avgs = agg.groupby(row_by)['AvgGrossVP'].mean().sort_values(ascending=False)
            row_labels = row_avgs.index.tolist()
        else:
            row_labels = sorted(row_labels, key=lambda x: (int(x) if str(x).isdigit() else 0, str(x)))

        # Optional TOTAL row
        if show_totals:
            totals = all_data.groupby('Hole', as_index=False)['GrossVP'].mean()
            totals.rename(columns={'GrossVP': 'AvgGrossVP'}, inplace=True)

        # Build HTML table
        html = ["<div class='table-responsive'><table class='teg-table heatmap-table'>"]
        html.append("<thead><tr><th></th>")
        for h in holes:
            html.append(f"<th>{h}</th>")
        html.append("<th>Avg</th></tr></thead><tbody>")

        for label in row_labels:
            row_data = agg[agg[row_by] == label]
            vals = {int(r['Hole']): r['AvgGrossVP'] for _, r in row_data.iterrows()}
            row_avg = row_data['AvgGrossVP'].mean()

            display_label = f"TEG {label}" if row_by == "TEGNum" else str(label)
            html.append(f"<tr><td class='row-label'>{display_label}</td>")
            for h in holes:
                v = vals.get(h, float('nan'))
                color = _heatmap_color(v)
                cell = f"{v:+.1f}" if not pd.isna(v) else ""
                html.append(f"<td style='{color}; text-align:center; font-size:0.8rem;'>{cell}</td>")
            # Row average
            color = _heatmap_color(row_avg)
            html.append(f"<td style='{color}; text-align:center; font-weight:600; font-size:0.8rem;'>{row_avg:+.1f}</td>")
            html.append("</tr>")

        # TOTAL row
        if show_totals:
            total_vals = {int(r['Hole']): r['AvgGrossVP'] for _, r in totals.iterrows()}
            total_avg = totals['AvgGrossVP'].mean()
            html.append("<tr class='total-row'><td class='row-label' style='font-weight:700;'>TOTAL</td>")
            for h in holes:
                v = total_vals.get(h, float('nan'))
                color = _heatmap_color(v)
                cell = f"{v:+.1f}" if not pd.isna(v) else ""
                html.append(f"<td style='{color}; text-align:center; font-weight:600; font-size:0.8rem;'>{cell}</td>")
            color = _heatmap_color(total_avg)
            html.append(f"<td style='{color}; text-align:center; font-weight:700; font-size:0.8rem;'>{total_avg:+.1f}</td>")
            html.append("</tr>")

        html.append("</tbody></table></div>")
        table_html = "".join(html)

        return {"table_html": table_html}
    except Exception as e:
        return {"error": str(e)}


def _parse_checkbox(val: str | None) -> bool:
    """Parse HTMX checkbox value: present='true' means checked, absent=None means unchecked."""
    return val is not None and val.lower() == "true"


@router.get("/scoring/heatmap")
async def scoring_heatmap_page(
    request: Request,
    row_by: str = Query("Player"),
    sort_by_score: str = Query("true"),
    show_totals: str = Query("true"),
):
    sbs = _parse_checkbox(sort_by_score)
    st = _parse_checkbox(show_totals)
    ctx = _heatmap_context(row_by, sbs, st)
    return templates.TemplateResponse("scoring_heatmap.html", {
        "request": request,
        "active_page": "scoring",
        "row_options": HEATMAP_ROWS,
        "row_by": row_by,
        "sort_by_score": sbs,
        "show_totals": st,
        **ctx,
    })


@router.get("/scoring/heatmap/content")
async def scoring_heatmap_content(
    request: Request,
    row_by: str = Query("Player"),
    sort_by_score: str | None = Query(None),
    show_totals: str | None = Query(None),
):
    sbs = _parse_checkbox(sort_by_score)
    st = _parse_checkbox(show_totals)
    ctx = _heatmap_context(row_by, sbs, st)
    return templates.TemplateResponse("partials/scoring_heatmap_content.html", {
        "request": request,
        **ctx,
    })
